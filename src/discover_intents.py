"""
Phase 5: Intent discovery from brand's actual support data.

Uses keyword-based categorization to derive a stable taxonomy, 
plus extracts independent escalation/risk metadata.

Produces:
  data/processed/intent_taxonomy.json
  reports/intent_taxonomy.md
"""

import json
import sys
import random
from collections import defaultdict
from src.config import DATA_PROCESSED, REPORTS, ensure_dirs

INTENT_DEFINITIONS = {
    "app_store_problems": {
        "intent_name": "app_store_problems",
        "definition": "Issues related to downloading, installing, updating, or using specific applications and the App Store.",
        "inclusion_criteria": "Mentions of apps crashing, freezing, failing to download, or App Store connectivity.",
        "exclusion_criteria": "Issues with native iOS functions like battery, or built-in Apple ID authentication.",
        "keywords": ["app", "apps", "download", "crash", "freeze", "app store", "spotify", "twitter", "instagram", "facebook"],
        "common_confusions": ["Confused with software_update_problems if an app crashes right after an iOS update.", "Confused with connectivity_network_services if the app won't load due to internet."]
    },
    "software_update_problems": {
        "intent_name": "software_update_problems",
        "definition": "Problems arising directly from or related to an iOS or macOS software update.",
        "inclusion_criteria": "Complaints about glitches, autocorrect bugs (e.g. 'I' to 'A ?'), or general lag immediately following an update.",
        "exclusion_criteria": "Hardware failure or battery drain unless explicitly linked to a recent update.",
        "keywords": ["update", "ios", "ios11", "upgrade", "upgraded", "glitch", "bug", "question mark box", "autocorrect", "keyboard", "fix", "lag"],
        "common_confusions": ["Confused with battery_charging_power since many users complain about battery drain after updating.", "Confused with app_store_problems when specific apps break on new OS."]
    },
    "battery_charging_power": {
        "intent_name": "battery_charging_power",
        "definition": "Issues concerning battery life, rapid draining, charging hardware, or device unexpectedly powering off.",
        "inclusion_criteria": "Mentions of battery dying fast, phone not charging, or power cord issues.",
        "exclusion_criteria": "Issues where the phone is completely unresponsive due to screen hardware failure.",
        "keywords": ["battery", "charge", "charging", "power", "drain", "die", "died", "cord", "cable", "plug"],
        "common_confusions": ["Confused with software_update_problems when users blame updates for battery drain.", "Confused with device_hardware_accessory if the charging port is physically broken."]
    },
    "device_hardware_accessory": {
        "intent_name": "device_hardware_accessory",
        "definition": "Physical hardware issues with devices (iPhone, iPad, Mac) or accessories (AirPods, Apple Watch, screens).",
        "inclusion_criteria": "Broken screens, unresponsive buttons, shattered glass, water damage, or accessory pairing issues.",
        "exclusion_criteria": "Software bugs that cause the screen to freeze, or battery/power issues.",
        "keywords": ["watch", "screen", "airpods", "macbook", "ipad", "broken", "repair", "glass", "button", "hardware", "crack", "display", "touch"],
        "common_confusions": ["Confused with connectivity_network_services if AirPods or Apple Watch won't pair via Bluetooth.", "Confused with app_store_problems if the screen freezes only inside an app."]
    },
    "apple_id_account": {
        "intent_name": "apple_id_account",
        "definition": "Issues regarding account access, Apple ID authentication, passwords, and iCloud backups.",
        "inclusion_criteria": "Locked accounts, forgotten passwords, iCloud storage limits, or two-factor authentication issues.",
        "exclusion_criteria": "Billing or payment failures not related to login credentials.",
        "keywords": ["apple id", "password", "account", "icloud", "login", "region", "authentication", "locked", "verification", "2fa"],
        "common_confusions": ["Confused with payments_purchases_billing when a user cannot buy an app because their account is locked.", "Confused with software_update_problems if iCloud backup fails during an update."]
    },
    "payments_purchases_billing": {
        "intent_name": "payments_purchases_billing",
        "definition": "Inquiries or complaints about unauthorized charges, refunds, subscriptions, and App Store purchases.",
        "inclusion_criteria": "Requests for refunds, unknown Apple charges on bank statements, or failed payment methods.",
        "exclusion_criteria": "Inability to login to make a purchase (belongs to Apple ID).",
        "keywords": ["bill", "payment", "paid", "refund", "subscription", "purchase", "card", "charged", "money", "invoice", "credit"],
        "common_confusions": ["Confused with app_store_problems when an in-app purchase fails.", "Confused with apple_id_account if a credit card is declined due to account region lock."]
    },
    "connectivity_network_services": {
        "intent_name": "connectivity_network_services",
        "definition": "Problems connecting to Wi-Fi, cellular networks, Bluetooth, or Apple services like iMessage and FaceTime.",
        "inclusion_criteria": "Dropped calls, 'No Service' messages, Wi-Fi grayed out, or iMessage failing to send.",
        "exclusion_criteria": "Hardware failure of the antenna, or account login issues preventing service access.",
        "keywords": ["wifi", "bluetooth", "cellular", "internet", "connect", "service", "imessage", "sms", "facetime", "drop", "network", "signal", "data"],
        "common_confusions": ["Confused with device_hardware_accessory for Bluetooth pairing issues.", "Confused with software_update_problems if a network issue arises immediately post-update."]
    },
    "general_support_other": {
        "intent_name": "general_support_other",
        "definition": "Catch-all category for broad support requests, general feedback, or inquiries lacking specific technical details.",
        "inclusion_criteria": "Vague requests for help, general compliments/complaints, or non-technical inquiries.",
        "exclusion_criteria": "Any message containing specific keywords that map to the other 7 distinct intents.",
        "keywords": ["help", "support", "issue", "problem", "question", "fix", "please", "why", "how"],
        "common_confusions": ["Often captures messages where the user provides an image/screenshot without text context."]
    }
}


def load_threads() -> list[dict]:
    path = DATA_PROCESSED / "threads.jsonl"
    if not path.exists():
        print("ERROR: Run build_threads first.")
        sys.exit(1)
    threads = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            threads.append(json.loads(line))
    return threads


def extract_customer_messages(threads: list[dict]) -> list[dict]:
    messages = []
    for t in threads:
        for msg in t["messages"]:
            if msg["author_type"] == "customer":
                messages.append({
                    "text": msg["text"],
                    "thread_id": t["thread_id"]
                })
                break
    return messages


def categorize_message(text: str) -> str:
    lower_text = text.lower()
    
    # Priority matching
    if any(k in lower_text for k in INTENT_DEFINITIONS["battery_charging_power"]["keywords"]):
        return "battery_charging_power"
    if any(k in lower_text for k in INTENT_DEFINITIONS["payments_purchases_billing"]["keywords"]):
        return "payments_purchases_billing"
    if any(k in lower_text for k in INTENT_DEFINITIONS["apple_id_account"]["keywords"]):
        return "apple_id_account"
    if any(k in lower_text for k in INTENT_DEFINITIONS["connectivity_network_services"]["keywords"]):
        return "connectivity_network_services"
    if any(k in lower_text for k in INTENT_DEFINITIONS["device_hardware_accessory"]["keywords"]):
        return "device_hardware_accessory"
    if any(k in lower_text for k in INTENT_DEFINITIONS["app_store_problems"]["keywords"]):
        return "app_store_problems"
    if any(k in lower_text for k in INTENT_DEFINITIONS["software_update_problems"]["keywords"]):
        return "software_update_problems"
        
    return "general_support_other"


def extract_metadata(text: str) -> dict:
    lower = text.lower()
    meta = {
        "high_frustration_angry": False,
        "repeated_unresolved_issue": False,
        "security_account_sensitive": False,
        "requires_private_dm_handling": False,
        "insufficient_context": False
    }
    
    angry_words = ["wtf", "fuck", "shit", "damn", "sucks", "terrible", "worst", "garbage", "trash", "hate", "pissed", "ridiculous"]
    if any(w in lower for w in angry_words) or sum(1 for c in text if c.isupper()) > len(text) * 0.5 or "!!!" in text:
        meta["high_frustration_angry"] = True
        
    repeated_words = ["again", "still", "second time", "third time", "keep", "keeps", "multiple times"]
    if any(w in lower for w in repeated_words):
        meta["repeated_unresolved_issue"] = True
        
    security_words = ["hack", "stolen", "fraud", "unauthorized", "charge", "password", "locked out"]
    if any(w in lower for w in security_words):
        meta["security_account_sensitive"] = True
        meta["requires_private_dm_handling"] = True
        
    if len(text.split()) < 4 and "http" in lower:
        meta["insufficient_context"] = True
        
    return meta


def build_taxonomy(messages: list[dict]) -> tuple:
    cluster_msgs = defaultdict(list)
    metadata_stats = defaultdict(int)
    
    for msg in messages:
        intent = categorize_message(msg["text"])
        meta = extract_metadata(msg["text"])
        
        cluster_msgs[intent].append(msg["text"])
        
        for k, v in meta.items():
            if v:
                metadata_stats[k] += 1
                
    taxonomy = []
    for intent_name, info in INTENT_DEFINITIONS.items():
        msgs = cluster_msgs[intent_name]
        random.seed(42)
        random.shuffle(msgs)
        
        pos_examples = [m for m in msgs if len(m.split()) > 5][:5]
        
        # Find confusing examples (msgs that contain keywords of other intents)
        confusing = []
        for m in msgs[5:]:
            lower = m.lower()
            other_matches = 0
            for other_intent, other_info in INTENT_DEFINITIONS.items():
                if other_intent != intent_name:
                    if any(k in lower for k in other_info["keywords"]):
                        other_matches += 1
            if other_matches >= 2:
                confusing.append(m)
            if len(confusing) >= 2:
                break
                
        if len(confusing) < 2:
            confusing.extend(msgs[10:12]) # Fallback
            
        freq = round(len(msgs) / max(len(messages), 1), 3)
        
        intent = {
            "intent_name": intent_name,
            "definition": info["definition"],
            "inclusion_criteria": info["inclusion_criteria"],
            "exclusion_criteria": info["exclusion_criteria"],
            "n_examples": len(msgs),
            "estimated_frequency": freq,
            "positive_examples": pos_examples,
            "confusing_examples": confusing[:2],
            "common_confusions": info["common_confusions"],
            "top_keywords": info["keywords"][:10],
        }
        taxonomy.append(intent)
        
    return taxonomy, metadata_stats


def write_taxonomy_md(taxonomy: list[dict], metadata_stats: dict, total_messages: int, path):
    lines = [
        "# Intent Taxonomy",
        "",
        f"**Total intents**: {len(taxonomy)}",
        f"**Total messages analyzed**: {total_messages:,}",
        "",
        "## Independent Metadata & Risk Layer",
        "These tags are evaluated independently of the intent classification to flag risk and handle routing.",
        ""
    ]
    
    for k, v in metadata_stats.items():
        freq = v / max(total_messages, 1)
        lines.append(f"- **{k}**: {v:,} examples ({freq:.1%})")
        
    lines.append("")
    lines.append("---")
    
    for intent in taxonomy:
        lines += [
            f"## {intent['intent_name']}",
            "",
            f"**Definition**: {intent['definition']}",
            f"**Inclusion Criteria**: {intent['inclusion_criteria']}",
            f"**Exclusion Criteria**: {intent['exclusion_criteria']}",
            f"**Frequency**: {intent['estimated_frequency']:.1%} ({intent['n_examples']:,} examples)",
            f"**Keywords**: {', '.join(intent['top_keywords'])}",
            "",
            "### Representative Examples",
            "",
        ]
        for ex in intent["positive_examples"]:
            lines.append(f"- {ex}")

        lines += ["", "### Confusing / Near-Boundary Examples", ""]
        for ex in intent["confusing_examples"]:
            lines.append(f"- {ex}")
            
        lines += ["", "### Major Confusions", ""]
        for c in intent["common_confusions"]:
            lines.append(f"- {c}")
            
        lines += ["", "---", ""]

    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    ensure_dirs()
    print("Loading threads...")
    threads = load_threads()
    messages = extract_customer_messages(threads)
    print(f"Extracted {len(messages):,} customer messages")

    taxonomy, metadata_stats = build_taxonomy(messages)

    # Save JSON
    out_json = DATA_PROCESSED / "intent_taxonomy.json"
    out_json.write_text(json.dumps(taxonomy, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved: {out_json}")

    # Save markdown
    out_md = REPORTS / "intent_taxonomy.md"
    write_taxonomy_md(taxonomy, metadata_stats, len(messages), out_md)
    print(f"Saved: {out_md}")

    # Summary
    print(f"\n{'='*50}")
    print(f"{'Intent':<30} {'Count':<8} {'Freq':<8}")
    print(f"{'-'*50}")
    for intent in sorted(taxonomy, key=lambda x: x["n_examples"], reverse=True):
        print(f"{intent['intent_name']:<30} {intent['n_examples']:<8} {intent['estimated_frequency']:.1%}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
