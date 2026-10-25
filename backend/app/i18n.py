"""Static UI/agent phrases in English, Tamil, Hindi and Odia.

Fixed phrases are hand-translated here so they work with no LLM at all.
Form-specific questions that are only written in English are translated
at runtime by the Translator agent (and cached per session).
Native speakers should review these before real use.
"""
from __future__ import annotations

LANGS = ("en", "ta", "hi", "or")

_M: dict[str, tuple[str, str, str, str]] = {
    "welcome": (
        "Let's fill the {form} together. I'll ask one question at a time. You can ask \"what does this mean?\" anytime, or say \"skip\" for optional questions.",
        "{form} படிவத்தை சேர்ந்து நிரப்புவோம். ஒரு நேரத்தில் ஒரு கேள்வி மட்டும் கேட்பேன். எப்போது வேண்டுமானாலும் \"இதன் அர்த்தம் என்ன?\" என்று கேட்கலாம், விருப்பக் கேள்விகளுக்கு \"skip\" என்று சொல்லலாம்.",
        "चलिए मिलकर {form} भरते हैं। मैं एक बार में एक ही सवाल पूछूँगा। आप कभी भी पूछ सकते हैं \"इसका मतलब क्या है?\", और वैकल्पिक सवालों के लिए \"skip\" कह सकते हैं।",
        "ଆସନ୍ତୁ ମିଶି {form} ପୂରଣ କରିବା। ମୁଁ ଥରକେ ଗୋଟିଏ ପ୍ରଶ୍ନ ପଚାରିବି। ଆପଣ ଯେକୌଣସି ସମୟରେ \"ଏହାର ଅର୍ଥ କ'ଣ?\" ପଚାରିପାରିବେ, ଏବଂ ଇଚ୍ଛାଧୀନ ପ୍ରଶ୍ନ ପାଇଁ \"skip\" କହିପାରିବେ।",
    ),
    "noted_value": (
        "Got it: {value}.",
        "சரி, குறித்துக்கொண்டேன்: {value}.",
        "ठीक है, नोट कर लिया: {value}।",
        "ଠିକ୍ ଅଛି, ଲେଖିନେଲି: {value}।",
    ),
    "ending_in": ("number ending in {last4}", "கடைசி இலக்கங்கள் {last4}", "आख़िरी अंक {last4}", "ଶେଷ ଅଙ୍କ {last4}"),
    "noted": ("Got it.", "சரி, குறித்துக்கொண்டேன்.", "ठीक है, नोट कर लिया।", "ଠିକ୍ ଅଛି, ଲେଖିନେଲି।"),
    "empty": (
        "I didn't catch that. Could you say it again?",
        "புரியவில்லை. மீண்டும் சொல்ல முடியுமா?",
        "मुझे समझ नहीं आया। क्या आप फिर से बता सकते हैं?",
        "ମୁଁ ବୁଝିପାରିଲି ନାହିଁ। ଦୟାକରି ପୁଣି କୁହନ୍ତୁ।",
    ),
    "needs_english": (
        "Official forms are filled in English letters. Please type it in English, exactly as on your ID card.",
        "அரசு படிவங்கள் ஆங்கில எழுத்துகளில் நிரப்பப்படும். உங்கள் அடையாள அட்டையில் உள்ளபடி ஆங்கிலத்தில் தட்டச்சு செய்யுங்கள்.",
        "सरकारी फॉर्म अंग्रेज़ी अक्षरों में भरे जाते हैं। कृपया अपने पहचान पत्र के अनुसार अंग्रेज़ी में लिखें।",
        "ସରକାରୀ ଫର୍ମ ଇଂରାଜୀ ଅକ୍ଷରରେ ପୂରଣ କରାଯାଏ। ଦୟାକରି ଆପଣଙ୍କ ପରିଚୟ ପତ୍ର ଅନୁସାରେ ଇଂରାଜୀରେ ଲେଖନ୍ତୁ।",
    ),
    "bad_name": (
        "That doesn't look like a name. Please give the name only, without numbers.",
        "இது பெயர் போல் இல்லை. எண்கள் இல்லாமல் பெயரை மட்டும் சொல்லுங்கள்.",
        "यह नाम जैसा नहीं लगता। कृपया बिना अंकों के केवल नाम बताएं।",
        "ଏହା ନାମ ପରି ଲାଗୁନାହିଁ। ଦୟାକରି ସଂଖ୍ୟା ବିନା କେବଳ ନାମ କୁହନ୍ତୁ।",
    ),
    "too_short": (
        "That seems too short. Please give the full details.",
        "இது மிகவும் சுருக்கமாக உள்ளது. முழு விவரத்தையும் சொல்லுங்கள்.",
        "यह बहुत छोटा है। कृपया पूरी जानकारी दें।",
        "ଏହା ବହୁତ ଛୋଟ। ଦୟାକରି ପୂରା ବିବରଣୀ ଦିଅନ୍ତୁ।",
    ),
    "bad_mobile": (
        "A mobile number has 10 digits and starts with 6, 7, 8 or 9. Please check it.",
        "மொபைல் எண்ணில் 10 இலக்கங்கள் இருக்கும், 6, 7, 8 அல்லது 9-இல் தொடங்கும். சரிபார்க்கவும்.",
        "मोबाइल नंबर 10 अंकों का होता है और 6, 7, 8 या 9 से शुरू होता है। कृपया जाँच लें।",
        "ମୋବାଇଲ ନମ୍ବର 10 ଅଙ୍କର ହୁଏ ଏବଂ 6, 7, 8 ବା 9 ରୁ ଆରମ୍ଭ ହୁଏ। ଦୟାକରି ଯାଞ୍ଚ କରନ୍ତୁ।",
    ),
    "bad_pincode": (
        "A PIN code has 6 digits and doesn't start with 0.",
        "அஞ்சல் குறியீட்டில் 6 இலக்கங்கள் இருக்கும், 0-வில் தொடங்காது.",
        "पिन कोड 6 अंकों का होता है और 0 से शुरू नहीं होता।",
        "ପିନ୍ କୋଡ୍ 6 ଅଙ୍କର ହୁଏ ଏବଂ 0 ରୁ ଆରମ୍ଭ ହୁଏ ନାହିଁ।",
    ),
    "bad_aadhaar": (
        "That Aadhaar number isn't valid. It has 12 digits - please check each digit on your card.",
        "இந்த ஆதார் எண் சரியில்லை. இதில் 12 இலக்கங்கள் உள்ளன - அட்டையில் ஒவ்வொரு இலக்கத்தையும் சரிபார்க்கவும்.",
        "यह आधार नंबर सही नहीं है। इसमें 12 अंक होते हैं - कृपया कार्ड पर हर अंक जाँचें।",
        "ଏହି ଆଧାର ନମ୍ବର ଠିକ୍ ନୁହେଁ। ଏଥିରେ 12 ଅଙ୍କ ଥାଏ - ଦୟାକରି କାର୍ଡରେ ପ୍ରତ୍ୟେକ ଅଙ୍କ ଯାଞ୍ଚ କରନ୍ତୁ।",
    ),
    "bad_pan": (
        "A PAN has 5 letters, 4 digits, then 1 letter - like ABCDE1234F.",
        "PAN-இல் 5 எழுத்துகள், 4 இலக்கங்கள், பிறகு 1 எழுத்து இருக்கும் - உதாரணம் ABCDE1234F.",
        "पैन में 5 अक्षर, 4 अंक और फिर 1 अक्षर होता है - जैसे ABCDE1234F।",
        "PAN ରେ 5 ଅକ୍ଷର, 4 ଅଙ୍କ, ତାପରେ 1 ଅକ୍ଷର ଥାଏ - ଯେପରି ABCDE1234F।",
    ),
    "bad_ifsc": (
        "An IFSC code has 11 characters: 4 letters, then 0, then 6 letters or digits (like SBIN0001234).",
        "IFSC குறியீட்டில் 11 எழுத்துகள்: 4 எழுத்துகள், பிறகு 0, பிறகு 6 எழுத்துகள் அல்லது இலக்கங்கள் (உதாரணம் SBIN0001234).",
        "IFSC कोड में 11 अक्षर होते हैं: 4 अक्षर, फिर 0, फिर 6 अक्षर या अंक (जैसे SBIN0001234)।",
        "IFSC କୋଡ୍‌ରେ 11 ଅକ୍ଷର ଥାଏ: 4 ଅକ୍ଷର, ତାପରେ 0, ତାପରେ 6 ଅକ୍ଷର ବା ଅଙ୍କ (ଯେପରି SBIN0001234)।",
    ),
    "bad_gstin": (
        "That GSTIN isn't valid. It has 15 characters - please copy it from your GST certificate.",
        "இந்த GSTIN சரியில்லை. இதில் 15 எழுத்துகள் உள்ளன - உங்கள் GST சான்றிதழில் இருந்து பார்த்து எழுதுங்கள்.",
        "यह GSTIN सही नहीं है। इसमें 15 अक्षर होते हैं - कृपया अपने GST प्रमाणपत्र से देखकर लिखें।",
        "ଏହି GSTIN ଠିକ୍ ନୁହେଁ। ଏଥିରେ 15 ଅକ୍ଷର ଥାଏ - ଦୟାକରି ଆପଣଙ୍କ GST ପ୍ରମାଣପତ୍ରରୁ ଦେଖି ଲେଖନ୍ତୁ।",
    ),
    "bad_account": (
        "A bank account number usually has 9 to 18 digits. Please check your passbook.",
        "வங்கிக் கணக்கு எண்ணில் பொதுவாக 9 முதல் 18 இலக்கங்கள் இருக்கும். பாஸ்புக்கைப் பார்க்கவும்.",
        "बैंक खाता नंबर आमतौर पर 9 से 18 अंकों का होता है। कृपया पासबुक देखें।",
        "ବ୍ୟାଙ୍କ ଖାତା ନମ୍ବର ସାଧାରଣତଃ 9 ରୁ 18 ଅଙ୍କର ହୁଏ। ଦୟାକରି ପାସବୁକ୍ ଦେଖନ୍ତୁ।",
    ),
    "bad_uan": (
        "A UAN has 12 digits. You can find it on your salary slip.",
        "UAN-இல் 12 இலக்கங்கள் இருக்கும். உங்கள் சம்பளச் சீட்டில் பார்க்கலாம்.",
        "UAN 12 अंकों का होता है। यह आपकी सैलरी स्लिप पर मिल जाएगा।",
        "UAN 12 ଅଙ୍କର ହୁଏ। ଏହା ଆପଣଙ୍କ ଦରମା ସ୍ଲିପ୍‌ରେ ମିଳିବ।",
    ),
    "bad_vehicle": (
        "Please give the registration number as on the RC, like TN 01 AB 1234.",
        "RC-யில் உள்ளபடி பதிவு எண்ணைச் சொல்லுங்கள், உதாரணம் TN 01 AB 1234.",
        "कृपया RC में लिखा रजिस्ट्रेशन नंबर बताएं, जैसे TN 01 AB 1234।",
        "ଦୟାକରି RC ରେ ଥିବା ପଞ୍ଜୀକରଣ ନମ୍ବର କୁହନ୍ତୁ, ଯେପରି OD 02 AB 1234।",
    ),
    "bad_email": (
        "That email address doesn't look right. It should be like name@example.com.",
        "இந்த மின்னஞ்சல் முகவரி சரியாக இல்லை. name@example.com போல இருக்க வேண்டும்.",
        "यह ईमेल पता सही नहीं लगता। यह name@example.com जैसा होना चाहिए।",
        "ଏହି ଇମେଲ ଠିକଣା ଠିକ୍ ଲାଗୁନାହିଁ। ଏହା name@example.com ପରି ହେବା ଉଚିତ।",
    ),
    "bad_date": (
        "Please give the date as day/month/year, like 15/08/1990.",
        "தேதியை நாள்/மாதம்/ஆண்டு வடிவில் சொல்லுங்கள், உதாரணம் 15/08/1990.",
        "कृपया तारीख दिन/महीना/साल में बताएं, जैसे 15/08/1990।",
        "ଦୟାକରି ତାରିଖ ଦିନ/ମାସ/ବର୍ଷ ଆକାରରେ କୁହନ୍ତୁ, ଯେପରି 15/08/1990।",
    ),
    "date_future": (
        "That date is in the future. Please check it.",
        "இந்தத் தேதி எதிர்காலத்தில் உள்ளது. சரிபார்க்கவும்.",
        "यह तारीख भविष्य की है। कृपया जाँच लें।",
        "ଏହି ତାରିଖ ଭବିଷ୍ୟତର। ଦୟାକରି ଯାଞ୍ଚ କରନ୍ତୁ।",
    ),
    "date_past": (
        "That date has already passed. This one needs a date that is still valid.",
        "இந்தத் தேதி ஏற்கனவே கடந்துவிட்டது. இன்னும் செல்லுபடியாகும் தேதி தேவை.",
        "यह तारीख बीत चुकी है। यहाँ ऐसी तारीख चाहिए जो अभी मान्य हो।",
        "ଏହି ତାରିଖ ବିତିଗଲାଣି। ଏଠାରେ ଏପରି ତାରିଖ ଦରକାର ଯାହା ଏବେ ବି ବୈଧ।",
    ),
    "not_adult": (
        "The applicant must be at least 18 years old for this form.",
        "இந்தப் படிவத்திற்கு விண்ணப்பதாரருக்கு குறைந்தது 18 வயது இருக்க வேண்டும்.",
        "इस फॉर्म के लिए आवेदक की उम्र कम से कम 18 साल होनी चाहिए।",
        "ଏହି ଫର୍ମ ପାଇଁ ଆବେଦକଙ୍କ ବୟସ ଅତି କମରେ 18 ବର୍ଷ ହେବା ଦରକାର।",
    ),
    "date_out_of_range": (
        "That date is outside the allowed range for this form.",
        "இந்தத் தேதி இந்தப் படிவத்திற்கு அனுமதிக்கப்பட்ட காலத்திற்கு வெளியே உள்ளது.",
        "यह तारीख इस फॉर्म की मान्य सीमा से बाहर है।",
        "ଏହି ତାରିଖ ଏହି ଫର୍ମର ଅନୁମୋଦିତ ସୀମା ବାହାରେ।",
    ),
    "bad_month_year": (
        "Please give the month and year, like 03/2026 or March 2026.",
        "மாதம் மற்றும் ஆண்டைச் சொல்லுங்கள், உதாரணம் 03/2026.",
        "कृपया महीना और साल बताएं, जैसे 03/2026।",
        "ଦୟାକରି ମାସ ଓ ବର୍ଷ କୁହନ୍ତୁ, ଯେପରି 03/2026।",
    ),
    "bad_amount": (
        "Please give the amount in numbers, like 25000 or 2.5 lakh.",
        "தொகையை எண்களில் சொல்லுங்கள், உதாரணம் 25000 அல்லது 2.5 lakh.",
        "कृपया राशि अंकों में बताएं, जैसे 25000 या 2.5 lakh।",
        "ଦୟାକରି ରାଶି ଅଙ୍କରେ କୁହନ୍ତୁ, ଯେପରି 25000 ବା 2.5 lakh।",
    ),
    "amount_range": (
        "That amount is outside the allowed range for this question.",
        "இந்தத் தொகை அனுமதிக்கப்பட்ட வரம்பிற்கு வெளியே உள்ளது.",
        "यह राशि इस सवाल की मान्य सीमा से बाहर है।",
        "ଏହି ରାଶି ଅନୁମୋଦିତ ସୀମା ବାହାରେ।",
    ),
    "bad_number": (
        "Please answer with a number.",
        "ஒரு எண்ணாகப் பதில் சொல்லுங்கள்.",
        "कृपया एक संख्या में जवाब दें।",
        "ଦୟାକରି ଏକ ସଂଖ୍ୟାରେ ଉତ୍ତର ଦିଅନ୍ତୁ।",
    ),
    "number_range": (
        "That number is outside the allowed range.",
        "இந்த எண் அனுமதிக்கப்பட்ட வரம்பிற்கு வெளியே உள்ளது.",
        "यह संख्या मान्य सीमा से बाहर है।",
        "ଏହି ସଂଖ୍ୟା ଅନୁମୋଦିତ ସୀମା ବାହାରେ।",
    ),
    "bad_choice": (
        "Please pick one of the options - you can reply with its number.",
        "கொடுக்கப்பட்ட விருப்பங்களில் ஒன்றைத் தேர்ந்தெடுங்கள் - அதன் எண்ணைச் சொன்னாலே போதும்.",
        "कृपया दिए गए विकल्पों में से एक चुनें - आप उसका नंबर भी बता सकते हैं।",
        "ଦୟାକରି ଦିଆଯାଇଥିବା ବିକଳ୍ପରୁ ଗୋଟିଏ ବାଛନ୍ତୁ - ଆପଣ ତାହାର ନମ୍ବର କହିପାରିବେ।",
    ),
    "cannot_skip": (
        "This one is required, so we can't skip it.",
        "இது கட்டாயம், எனவே தவிர்க்க முடியாது.",
        "यह ज़रूरी है, इसलिए इसे छोड़ नहीं सकते।",
        "ଏହା ବାଧ୍ୟତାମୂଳକ, ତେଣୁ ଛାଡିହେବ ନାହିଁ।",
    ),
    "skipped": ("Okay, skipped.", "சரி, தவிர்த்துவிட்டேன்.", "ठीक है, छोड़ दिया।", "ଠିକ୍ ଅଛି, ଛାଡିଦେଲି।"),
    "review_intro": (
        "All questions are done. Please check your details:",
        "எல்லாக் கேள்விகளும் முடிந்தன. உங்கள் விவரங்களைச் சரிபார்க்கவும்:",
        "सभी सवाल पूरे हो गए। कृपया अपनी जानकारी जाँच लें:",
        "ସବୁ ପ୍ରଶ୍ନ ସରିଗଲା। ଦୟାକରି ଆପଣଙ୍କ ବିବରଣୀ ଯାଞ୍ଚ କରନ୍ତୁ:",
    ),
    "documents_title": (
        "Documents to bring:",
        "கொண்டு வர வேண்டிய ஆவணங்கள்:",
        "साथ लाने वाले दस्तावेज़:",
        "ସାଥିରେ ଆଣିବାକୁ ଥିବା ଦସ୍ତାବିଜ:",
    ),
    "warnings_title": ("Please double-check:", "மீண்டும் சரிபார்க்கவும்:", "कृपया दोबारा जाँचें:", "ଦୟାକରି ପୁଣି ଯାଞ୍ଚ କରନ୍ତୁ:"),
    "confirm_prompt": (
        "Is everything correct? Say \"yes\" to finish, or tell me what to change (for example \"change mobile number\").",
        "எல்லாம் சரியா? முடிக்க \"ஆம்\" என்று சொல்லுங்கள், அல்லது எதை மாற்ற வேண்டும் என்று சொல்லுங்கள் (உதாரணம் \"மொபைல் எண்ணை மாற்று\").",
        "क्या सब सही है? पूरा करने के लिए \"हाँ\" कहें, या बताएं क्या बदलना है (जैसे \"मोबाइल नंबर बदलो\")।",
        "ସବୁ ଠିକ୍ ଅଛି କି? ସାରିବାକୁ \"ହଁ\" କୁହନ୍ତୁ, କିମ୍ବା କ'ଣ ବଦଳାଇବାକୁ ହେବ କୁହନ୍ତୁ (ଯେପରି \"ମୋବାଇଲ ନମ୍ବର ବଦଳାଅ\")।",
    ),
    "completed": (
        "Done! Your filled form is ready. Download the PDF, copy these details onto the official form, and carry the documents listed.",
        "முடிந்தது! உங்கள் நிரப்பிய படிவம் தயார். PDF-ஐப் பதிவிறக்கி, இந்த விவரங்களை அதிகாரப்பூர்வ படிவத்தில் எழுதுங்கள், பட்டியலிட்ட ஆவணங்களைக் கொண்டு செல்லுங்கள்.",
        "हो गया! आपका भरा हुआ फॉर्म तैयार है। PDF डाउनलोड करें, ये जानकारी असली फॉर्म में लिखें, और बताए गए दस्तावेज़ साथ ले जाएं।",
        "ସରିଗଲା! ଆପଣଙ୍କ ପୂରଣ ହୋଇଥିବା ଫର୍ମ ପ୍ରସ୍ତୁତ। PDF ଡାଉନଲୋଡ୍ କରନ୍ତୁ, ଏହି ବିବରଣୀ ସରକାରୀ ଫର୍ମରେ ଲେଖନ୍ତୁ, ଏବଂ ତାଲିକାରେ ଥିବା ଦସ୍ତାବିଜ ନେଇଯାଆନ୍ତୁ।",
    ),
    "already_complete": (
        "This form is already complete. You can download the PDF, or say \"change\" and the detail name to edit something.",
        "இந்தப் படிவம் ஏற்கனவே முடிந்தது. PDF-ஐப் பதிவிறக்கலாம், அல்லது ஏதாவது மாற்ற \"மாற்று\" என்று சொல்லலாம்.",
        "यह फॉर्म पहले ही पूरा हो चुका है। आप PDF डाउनलोड कर सकते हैं, या कुछ बदलने के लिए \"बदलो\" कहें।",
        "ଏହି ଫର୍ମ ପୂର୍ବରୁ ସରିଛି। ଆପଣ PDF ଡାଉନଲୋଡ୍ କରିପାରିବେ, କିମ୍ବା କିଛି ବଦଳାଇବାକୁ \"ବଦଳାଅ\" କୁହନ୍ତୁ।",
    ),
    "which_field": (
        "Which detail do you want to change? Say its name, like \"mobile number\".",
        "எந்த விவரத்தை மாற்ற வேண்டும்? அதன் பெயரைச் சொல்லுங்கள், உதாரணம் \"மொபைல் எண்\".",
        "आप कौन सी जानकारी बदलना चाहते हैं? उसका नाम बताएं, जैसे \"मोबाइल नंबर\"।",
        "ଆପଣ କେଉଁ ବିବରଣୀ ବଦଳାଇବାକୁ ଚାହାଁନ୍ତି? ତାହାର ନାମ କୁହନ୍ତୁ, ଯେପରି \"ମୋବାଇଲ ନମ୍ବର\"।",
    ),
    "corrected": (
        "Sure, let's change {label}.",
        "சரி, {label}-ஐ மாற்றுவோம்.",
        "ठीक है, {label} बदलते हैं।",
        "ଠିକ୍ ଅଛି, {label} ବଦଳାଇବା।",
    ),
    "choose_option": (
        "Reply with the number or the option:",
        "எண்ணையோ விருப்பத்தையோ சொல்லுங்கள்:",
        "नंबर या विकल्प बताएं:",
        "ନମ୍ବର ବା ବିକଳ୍ପ କୁହନ୍ତୁ:",
    ),
    "optional_hint": (
        "(optional - say \"skip\" to leave it blank)",
        "(விருப்பம் - காலியாக விட \"skip\" என்று சொல்லுங்கள்)",
        "(वैकल्पिक - खाली छोड़ने के लिए \"skip\" कहें)",
        "(ଇଚ୍ଛାଧୀନ - ଖାଲି ଛାଡିବାକୁ \"skip\" କୁହନ୍ତୁ)",
    ),
    "explain_prefix": ("Here's what this means:", "இதன் அர்த்தம்:", "इसका मतलब है:", "ଏହାର ଅର୍ଥ:"),
    "generic_ask": (
        "Please tell me: {label}",
        "தயவுசெய்து சொல்லுங்கள்: {label}",
        "कृपया बताएं: {label}",
        "ଦୟାକରି କୁହନ୍ତୁ: {label}",
    ),
    "pick_form": (
        "Which form do you need help with? Tell me in your own words, like \"new electricity connection for my house\".",
        "எந்தப் படிவத்திற்கு உதவி வேண்டும்? உங்கள் சொந்த வார்த்தைகளில் சொல்லுங்கள், உதாரணம் \"என் வீட்டிற்கு புதிய மின் இணைப்பு\".",
        "आपको किस फॉर्म में मदद चाहिए? अपने शब्दों में बताएं, जैसे \"मेरे घर के लिए नया बिजली कनेक्शन\"।",
        "ଆପଣଙ୍କୁ କେଉଁ ଫର୍ମରେ ସାହାଯ୍ୟ ଦରକାର? ନିଜ ଭାଷାରେ କୁହନ୍ତୁ, ଯେପରି \"ମୋ ଘର ପାଇଁ ନୂଆ ବିଦ୍ୟୁତ୍ ସଂଯୋଗ\"।",
    ),
    "yes": ("Yes", "ஆம்", "हाँ", "ହଁ"),
    "no": ("No", "இல்லை", "नहीं", "ନା"),
}


def msg(key: str, lang: str = "en", **kwargs) -> str:
    row = _M.get(key)
    if row is None:
        return key
    idx = LANGS.index(lang) if lang in LANGS else 0
    return row[idx].format(**kwargs) if kwargs else row[idx]


def loc(obj, lang: str = "en") -> str:
    """Pick the right language from a {'en':..,'ta':..} dict (or return a plain string)."""
    if isinstance(obj, dict):
        return obj.get(lang) or obj.get("en") or next(iter(obj.values()), "")
    return obj or ""


def has_translation(obj, lang: str) -> bool:
    return lang == "en" or (isinstance(obj, dict) and bool(obj.get(lang)))
