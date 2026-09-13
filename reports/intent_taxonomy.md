# Intent Taxonomy

**Total intents**: 8
**Total messages analyzed**: 81,481

## Independent Metadata & Risk Layer
These tags are evaluated independently of the intent classification to flag risk and handle routing.

- **insufficient_context**: 426 examples (0.5%)
- **repeated_unresolved_issue**: 9,307 examples (11.4%)
- **high_frustration_angry**: 16,157 examples (19.8%)
- **security_account_sensitive**: 3,238 examples (4.0%)
- **requires_private_dm_handling**: 3,238 examples (4.0%)

---
## app_store_problems

**Definition**: Issues related to downloading, installing, updating, or using specific applications and the App Store.
**Inclusion Criteria**: Mentions of apps crashing, freezing, failing to download, or App Store connectivity.
**Exclusion Criteria**: Issues with native iOS functions like battery, or built-in Apple ID authentication.
**Frequency**: 46.3% (37,762 examples)
**Keywords**: app, apps, download, crash, freeze, app store, spotify, twitter, instagram, facebook

### Representative Examples

- @AppleSupport I’ve currently made an appointment at the Genius Bar for this weekend, I was previously told to restore the phone and this has made it worse
- If you haven't upgraded to IOS 11, DO NOT DO IT. @AppleSupport has killed my phone, freezing, apps crashing, phone rebooting, ridiculous.
- CARALHO DE ASA MINHA GALERIA ZEROU DO NADA, já reiniciei e tudo, APPLE FILHA DA PUTA @AppleSupport @115858 VAI TOMA NO CU DESGRACADOS
- @AppleSupport @118936 @23150 @160959 I️ I️ I️ I️ I️ I️ I️ I️ I️ I️ I️ I️ I️ I️ please help I️ I️ I️ I️ I️
- @AppleSupport Thank you @AppleSupport I wasn’t expecting a response, but thanks for the excellent support.

### Confusing / Near-Boundary Examples

- @AppleSupport so I have the latest iOS and I still get the question mark https://t.co/dxoiSVBGXn
- @115858 @AppleSupport  please tell me y’all are fixing the I️ problem immediately

### Major Confusions

- Confused with software_update_problems if an app crashes right after an iOS update.
- Confused with connectivity_network_services if the app won't load due to internet.

---

## software_update_problems

**Definition**: Problems arising directly from or related to an iOS or macOS software update.
**Inclusion Criteria**: Complaints about glitches, autocorrect bugs (e.g. 'I' to 'A ?'), or general lag immediately following an update.
**Exclusion Criteria**: Hardware failure or battery drain unless explicitly linked to a recent update.
**Frequency**: 13.6% (11,108 examples)
**Keywords**: update, ios, ios11, upgrade, upgraded, glitch, bug, question mark box, autocorrect, keyboard

### Representative Examples

- The new iPhone update is super glitchy. @115858 please fix.
- Bruh @115858 I don’t think I’ve had an update mess up my phone as much as the iOS 11 did 🙃
- @115858 look at how ugly my caption is !!! FIX THISSSS
- @115858 Fix My Phone Please. The iPhone 4 was faster than this iPhone. Smh.
- @115858 get y’all shit together. My phone been messing up since I updated it

### Confusing / Near-Boundary Examples

- Completed @115858 iOS iphone update, switching to #Samsung @115858 updates are for #tweens, super #buggy, frustrating! https://t.co/OPupCPuQAZ
- @116333 How about giving us iOS updates that don’t brick our POS IPHONES? I make a living dependent largely on my phone and am thinking android!!

### Major Confusions

- Confused with battery_charging_power since many users complain about battery drain after updating.
- Confused with app_store_problems when specific apps break on new OS.

---

## battery_charging_power

**Definition**: Issues concerning battery life, rapid draining, charging hardware, or device unexpectedly powering off.
**Inclusion Criteria**: Mentions of battery dying fast, phone not charging, or power cord issues.
**Exclusion Criteria**: Issues where the phone is completely unresponsive due to screen hardware failure.
**Frequency**: 12.7% (10,325 examples)
**Keywords**: battery, charge, charging, power, drain, die, died, cord, cable, plug

### Representative Examples

- WTF @AppleSupport, iPhone 6s plus battery only lasting half a day after iOS 11 upgrades 😠😡 !
- @115858 u give us 3 s*** updates that my 69% #iphone battery dies 28 min N2 @203 #mapmyrun &amp; enjoying @103932 pod #comeonman
- Hey @115858 , ios11 keeps my battery draining yo , and the layout of ios10 much better than now , disappointed boy
- @AppleSupport Battery is draining like android
- Never saw any problem with my charger till yesterday when it decided to split in half @115858 fix ya damn trash chargers

### Confusing / Near-Boundary Examples

- phone just died on 40% then when i plugged it in it was back on 40% then it went down to 10% rapid @AppleSupport EXPLAIN YOURSELF
- @AppleSupport iphone 6s getting hang battery issue app issue after installing ios 11 😡

### Major Confusions

- Confused with software_update_problems when users blame updates for battery drain.
- Confused with device_hardware_accessory if the charging port is physically broken.

---

## device_hardware_accessory

**Definition**: Physical hardware issues with devices (iPhone, iPad, Mac) or accessories (AirPods, Apple Watch, screens).
**Inclusion Criteria**: Broken screens, unresponsive buttons, shattered glass, water damage, or accessory pairing issues.
**Exclusion Criteria**: Software bugs that cause the screen to freeze, or battery/power issues.
**Frequency**: 8.8% (7,185 examples)
**Keywords**: watch, screen, airpods, macbook, ipad, broken, repair, glass, button, hardware

### Representative Examples

- For instance @115858 when are you gunna fix my fuckin I button I️ refuse to change it in my shortcuts it shouldn’t come down to this
- @AppleSupport why does an Ipad has trouble working with an apple Keyboard? You got it, IOS upgrade!!! Please work on solving this,got the apple keyboard to avoid issues and now 👎🏼
- Ok so face recognition isn't always working AND.... maybe something going on with the display.  @115858 here I come !
- @AppleSupport can’t log in to forum on phone. High Sierra has killed my Mac Mini. Screen goes black in middle of boot. Even if left alone for 4 hours. Recovery mode is High Sierra, screen goes black 30 minutes into 1 hour plus install.
- @AppleSupport Having intermittent touch unresponsiveness with my 6s after upgrading to iOS 11.0.3. Any tips or suggestions?

### Confusing / Near-Boundary Examples

- I also cannot access the homescreen from here anymore. Only thing left is to reboot :( @AppleSupport https://t.co/lebgnV7XGp
- @AppleSupport my Apple Music won’t open screen blacks out and take me back home

### Major Confusions

- Confused with connectivity_network_services if AirPods or Apple Watch won't pair via Bluetooth.
- Confused with app_store_problems if the screen freezes only inside an app.

---

## apple_id_account

**Definition**: Issues regarding account access, Apple ID authentication, passwords, and iCloud backups.
**Inclusion Criteria**: Locked accounts, forgotten passwords, iCloud storage limits, or two-factor authentication issues.
**Exclusion Criteria**: Billing or payment failures not related to login credentials.
**Frequency**: 3.6% (2,955 examples)
**Keywords**: apple id, password, account, icloud, login, region, authentication, locked, verification, 2fa

### Representative Examples

- @AppleSupport my and my fiancée have been getting a call from Apple about iCloud security . Scam?
- @AppleSupport I’m trying to download my 22GB iPhoto iCloud history to my new iPhone, but there’s no sign of it working. What do I need to do?
- So the keyboard issue is fixed, now my lock screen won’t show the clock, notifications, music or allow me to swipe over to widgets. This is all I see while locked. @AppleSupport I’ve done several restarts and it comes back only for a few minutes then goes back. https://t.co/3S7bzuixEw
- One major issue reported by me regarding fingerprint authentication in apple developers login &amp; on forum. Still no revert :-( @AppleSupport
- @AppleSupport https://t.co/DcSrdWNuPm says “Photos is locked” and full-res photos can’t be downloaded. Since about at least 3PM EST.

### Confusing / Near-Boundary Examples

- @AppleSupport umm can I get some help with my Apple ID guys.
- @AppleSupport 3. Apple employee seemed not understand iCloud, photos, or care abt distraught customer &amp; her memories.

### Major Confusions

- Confused with payments_purchases_billing when a user cannot buy an app because their account is locked.
- Confused with software_update_problems if iCloud backup fails during an update.

---

## payments_purchases_billing

**Definition**: Inquiries or complaints about unauthorized charges, refunds, subscriptions, and App Store purchases.
**Inclusion Criteria**: Requests for refunds, unknown Apple charges on bank statements, or failed payment methods.
**Exclusion Criteria**: Inability to login to make a purchase (belongs to Apple ID).
**Frequency**: 2.6% (2,152 examples)
**Keywords**: bill, payment, paid, refund, subscription, purchase, card, charged, money, invoice

### Representative Examples

- @AppleSupport which Indian banks support iTunes payment?
- @AppleSupport, I didn’t sign up for localized album covers, how do I disable this crap?

iPhone language: English (U.K.)
Region: United Kingdom

Yes, my payment country is Russia. https://t.co/rjwxymSDwy
- My phone can’t even make fucking calls or play music thru headphones. Not even a year old no cracks nothin. Run me my money @115858 https://t.co/fmPvCbzjvk
- @AppleSupport Hi- preordered Reputation on iTunes and it says purchased. Can download on my iPad but not iPhone? It downloads the goes back to not being on the iPhone. In music I click on the song and it just says loading. Thanks
- @AppleSupport happy friday my apple gurus, I have email for reservation but no purchase email.  Mine is still due Nov 3rd yes?  Awesome!

### Confusing / Near-Boundary Examples

- Hey @115858 can you fix your latest iOS patch? My 6s keeps losing audio functions and crashing this is not what I paid $400 for
- @AppleSupport I can’t downloads apps . Keep saying declined payment I never brought anything https://t.co/HQJQOvXyxW

### Major Confusions

- Confused with app_store_problems when an in-app purchase fails.
- Confused with apple_id_account if a credit card is declined due to account region lock.

---

## connectivity_network_services

**Definition**: Problems connecting to Wi-Fi, cellular networks, Bluetooth, or Apple services like iMessage and FaceTime.
**Inclusion Criteria**: Dropped calls, 'No Service' messages, Wi-Fi grayed out, or iMessage failing to send.
**Exclusion Criteria**: Hardware failure of the antenna, or account login issues preventing service access.
**Frequency**: 6.4% (5,185 examples)
**Keywords**: wifi, bluetooth, cellular, internet, connect, service, imessage, sms, facetime, drop

### Representative Examples

- @AppleSupport @115858 since the iOS 11.0 3 update its been hell with Bluetooth connectivity. Many are having the same issue. Please help
- @AppleSupport first time I regreted that Ive updated my OS.. low sierra:( lost my all data:(
- @115858 so the customer service guy I spoke told me flat out i have a 1200 paper weight untill @att gets us servers up
- @AppleSupport Says can't connect to server, etc or nothing happens. I'm at my wits end now. I've tried everything with the hotline who asked me to backup, wipe and restore. Now i can't launch any of my store apps, my life is on LINE and whatsapp... help me.
- @AppleSupport After iOS 11.0.3 update on iPhone7.WiFi shows that I'm connected but it doesn't use WiFi.1st time I used all my 12GB n a month

### Confusing / Near-Boundary Examples

- @AppleSupport iPhone freezed for 6 hours. After following your thread on how to solve the issue I lost all my data. I'm moving to Android!!🤬
- @AppleSupport You seriously need to fix IOS 11 updates. I have brand new iPhone 7+ and had to rest network settings several times.

### Major Confusions

- Confused with device_hardware_accessory for Bluetooth pairing issues.
- Confused with software_update_problems if a network issue arises immediately post-update.

---

## general_support_other

**Definition**: Catch-all category for broad support requests, general feedback, or inquiries lacking specific technical details.
**Inclusion Criteria**: Vague requests for help, general compliments/complaints, or non-technical inquiries.
**Exclusion Criteria**: Any message containing specific keywords that map to the other 7 distinct intents.
**Frequency**: 5.9% (4,809 examples)
**Keywords**: help, support, issue, problem, question, fix, please, why, how

### Representative Examples

- @115858 wtf is going on why is my “I️” changing to this weird thing
- My phones volume just stopped working. I have everything on full blast, zero sound. This phone is fucking trash. Fuck you @115858
- Finally what the fuck is up with these question marks @115858
- @115858 releases overpriced @797 and suddenly my iPhone camera stops working. GTFOH!! @136958 please stop this bull shiitake!
- @115858 Ho un problema quando uso il mio compleanno

### Confusing / Near-Boundary Examples

- Wtf is wrong with the iphone 7 lately 🤔🤔 @115858 my phone does whatever it wants 🙄
- @115858 I️ I️ I️ wtf is this man

### Major Confusions

- Often captures messages where the user provides an image/screenshot without text context.

---
