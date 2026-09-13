# Golden Set Labeling Guidelines

## Purpose
These guidelines help human reviewers validate and correct the auto-generated labels
in the golden evaluation set.

## Intent Labels

Each message should be assigned exactly ONE intent from the taxonomy below.

### app_store_problems
**Definition**: Issues related to downloading, installing, updating, or using specific applications and the App Store.
**Inclusion**: Mentions of apps crashing, freezing, failing to download, or App Store connectivity.
**Exclusion**: Issues with native iOS functions like battery, or built-in Apple ID authentication.

**Positive examples:**
- @AppleSupport I’ve currently made an appointment at the Genius Bar for this weekend, I was previously told to restore the phone and this has made it w...
- If you haven't upgraded to IOS 11, DO NOT DO IT. @AppleSupport has killed my phone, freezing, apps crashing, phone rebooting, ridiculous....
- CARALHO DE ASA MINHA GALERIA ZEROU DO NADA, já reiniciei e tudo, APPLE FILHA DA PUTA @AppleSupport @115858 VAI TOMA NO CU DESGRACADOS...

### software_update_problems
**Definition**: Problems arising directly from or related to an iOS or macOS software update.
**Inclusion**: Complaints about glitches, autocorrect bugs (e.g. 'I' to 'A ?'), or general lag immediately following an update.
**Exclusion**: Hardware failure or battery drain unless explicitly linked to a recent update.

**Positive examples:**
- The new iPhone update is super glitchy. @115858 please fix....
- Bruh @115858 I don’t think I’ve had an update mess up my phone as much as the iOS 11 did 🙃...
- @115858 look at how ugly my caption is !!! FIX THISSSS...

### battery_charging_power
**Definition**: Issues concerning battery life, rapid draining, charging hardware, or device unexpectedly powering off.
**Inclusion**: Mentions of battery dying fast, phone not charging, or power cord issues.
**Exclusion**: Issues where the phone is completely unresponsive due to screen hardware failure.

**Positive examples:**
- WTF @AppleSupport, iPhone 6s plus battery only lasting half a day after iOS 11 upgrades 😠😡 !...
- @115858 u give us 3 s*** updates that my 69% #iphone battery dies 28 min N2 @203 #mapmyrun &amp; enjoying @103932 pod #comeonman...
- Hey @115858 , ios11 keeps my battery draining yo , and the layout of ios10 much better than now , disappointed boy...

### device_hardware_accessory
**Definition**: Physical hardware issues with devices (iPhone, iPad, Mac) or accessories (AirPods, Apple Watch, screens).
**Inclusion**: Broken screens, unresponsive buttons, shattered glass, water damage, or accessory pairing issues.
**Exclusion**: Software bugs that cause the screen to freeze, or battery/power issues.

**Positive examples:**
- For instance @115858 when are you gunna fix my fuckin I button I️ refuse to change it in my shortcuts it shouldn’t come down to this...
- @AppleSupport why does an Ipad has trouble working with an apple Keyboard? You got it, IOS upgrade!!! Please work on solving this,got the apple keyboa...
- Ok so face recognition isn't always working AND.... maybe something going on with the display.  @115858 here I come !...

### apple_id_account
**Definition**: Issues regarding account access, Apple ID authentication, passwords, and iCloud backups.
**Inclusion**: Locked accounts, forgotten passwords, iCloud storage limits, or two-factor authentication issues.
**Exclusion**: Billing or payment failures not related to login credentials.

**Positive examples:**
- @AppleSupport my and my fiancée have been getting a call from Apple about iCloud security . Scam?...
- @AppleSupport I’m trying to download my 22GB iPhoto iCloud history to my new iPhone, but there’s no sign of it working. What do I need to do?...
- So the keyboard issue is fixed, now my lock screen won’t show the clock, notifications, music or allow me to swipe over to widgets. This is all I see ...

### payments_purchases_billing
**Definition**: Inquiries or complaints about unauthorized charges, refunds, subscriptions, and App Store purchases.
**Inclusion**: Requests for refunds, unknown Apple charges on bank statements, or failed payment methods.
**Exclusion**: Inability to login to make a purchase (belongs to Apple ID).

**Positive examples:**
- @AppleSupport which Indian banks support iTunes payment?...
- @AppleSupport, I didn’t sign up for localized album covers, how do I disable this crap?

iPhone language: English (U.K.)
Region: United Kingdom

Yes, ...
- My phone can’t even make fucking calls or play music thru headphones. Not even a year old no cracks nothin. Run me my money @115858 https://t.co/fmPvC...

### connectivity_network_services
**Definition**: Problems connecting to Wi-Fi, cellular networks, Bluetooth, or Apple services like iMessage and FaceTime.
**Inclusion**: Dropped calls, 'No Service' messages, Wi-Fi grayed out, or iMessage failing to send.
**Exclusion**: Hardware failure of the antenna, or account login issues preventing service access.

**Positive examples:**
- @AppleSupport @115858 since the iOS 11.0 3 update its been hell with Bluetooth connectivity. Many are having the same issue. Please help...
- @AppleSupport first time I regreted that Ive updated my OS.. low sierra:( lost my all data:(...
- @115858 so the customer service guy I spoke told me flat out i have a 1200 paper weight untill @att gets us servers up...

### general_support_other
**Definition**: Catch-all category for broad support requests, general feedback, or inquiries lacking specific technical details.
**Inclusion**: Vague requests for help, general compliments/complaints, or non-technical inquiries.
**Exclusion**: Any message containing specific keywords that map to the other 7 distinct intents.

**Positive examples:**
- @115858 wtf is going on why is my “I️” changing to this weird thing...
- My phones volume just stopped working. I have everything on full blast, zero sound. This phone is fucking trash. Fuck you @115858...
- Finally what the fuck is up with these question marks @115858...

## Escalation Criteria

Mark `human_editable_escalation = True` if ANY of the following apply:

1. **Security concern**: Account compromise, unauthorized access, data breach
2. **Legal/regulatory**: Mentions of lawyers, lawsuits, regulatory complaints
3. **Repeated unresolved**: Customer indicates prior failed resolution attempts
4. **Extreme anger**: Hostile, threatening, or deeply dissatisfied customer
5. **Complex multi-issue**: Multiple intertwined problems requiring investigation
6. **High-impact financial**: Large disputed amounts, billing errors
7. **Safety concern**: Any threat or safety-related situation

Mark `human_editable_escalation = False` for routine inquiries, standard requests,
and issues with clear resolution paths.

## Labeling Process

1. Read the `text` and `context`.
2. Review `human_editable_intent` (initially auto-filled). Correct it if needed.
3. Review `human_editable_escalation` (initially auto-filled). Correct it if needed.
4. If escalating, provide an `escalation_reason`.
5. Change `label_status` to `human_reviewed` when done.