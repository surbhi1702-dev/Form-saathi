import type { Lang } from "./types";

export const LANGUAGES: { code: Lang; name: string; english: string; speech: string }[] = [
  { code: "ta", name: "தமிழ்", english: "Tamil", speech: "ta-IN" },
  { code: "hi", name: "हिन्दी", english: "Hindi", speech: "hi-IN" },
  { code: "or", name: "ଓଡ଼ିଆ", english: "Odia", speech: "or-IN" },
  { code: "en", name: "English", english: "English", speech: "en-IN" },
];

type Strings = Record<string, [string, string, string, string]>; // en, ta, hi, or

const S: Strings = {
  tagline: [
    "Fill any form in your own language, one question at a time.",
    "எந்தப் படிவத்தையும் உங்கள் மொழியில், ஒவ்வொரு கேள்வியாக நிரப்புங்கள்.",
    "कोई भी फॉर्म अपनी भाषा में, एक-एक सवाल करके भरें।",
    "ଯେକୌଣସି ଫର୍ମ ନିଜ ଭାଷାରେ, ଗୋଟିଏ ଗୋଟିଏ ପ୍ରଶ୍ନ କରି ପୂରଣ କରନ୍ତୁ।",
  ],
  chooseLanguage: ["Choose your language", "உங்கள் மொழியைத் தேர்ந்தெடுங்கள்", "अपनी भाषा चुनें", "ଆପଣଙ୍କ ଭାଷା ବାଛନ୍ତୁ"],
  whatNeed: ["What do you need to fill?", "எதை நிரப்ப வேண்டும்?", "आपको क्या भरना है?", "ଆପଣଙ୍କୁ କ'ଣ ପୂରଣ କରିବାକୁ ଅଛି?"],
  whatNeedPlaceholder: [
    "For example: new gas connection",
    "உதாரணம்: புதிய கேஸ் இணைப்பு",
    "जैसे: नया गैस कनेक्शन",
    "ଯେପରି: ନୂଆ ଗ୍ୟାସ ସଂଯୋଗ",
  ],
  findForm: ["Find my form", "படிவத்தைத் தேடு", "फॉर्म खोजें", "ଫର୍ମ ଖୋଜନ୍ତୁ"],
  noMatch: [
    "No form matched. Pick one from the list below.",
    "எந்தப் படிவமும் பொருந்தவில்லை. கீழே உள்ள பட்டியலில் இருந்து தேர்ந்தெடுங்கள்.",
    "कोई फॉर्म नहीं मिला। नीचे की सूची से चुनें।",
    "କୌଣସି ଫର୍ମ ମିଳିଲା ନାହିଁ। ତଳ ତାଲିକାରୁ ବାଛନ୍ତୁ।",
  ],
  allForms: ["All forms", "எல்லாப் படிவங்களும்", "सभी फॉर्म", "ସବୁ ଫର୍ମ"],
  questions: ["{n} questions", "{n} கேள்விகள்", "{n} सवाल", "{n}ଟି ପ୍ରଶ୍ନ"],
  scanTitle: ["Have a different form?", "வேறு படிவம் உள்ளதா?", "कोई और फॉर्म है?", "ଅନ୍ୟ କୌଣସି ଫର୍ମ ଅଛି କି?"],
  scanBody: [
    "Upload a clear photo of it and Form Saathi will read its questions.",
    "அதன் தெளிவான புகைப்படத்தைப் பதிவேற்றுங்கள், Form Saathi அதன் கேள்விகளைப் படிக்கும்.",
    "उसकी साफ़ फ़ोटो अपलोड करें, Form Saathi उसके सवाल पढ़ लेगा।",
    "ତାହାର ସ୍ପଷ୍ଟ ଫଟୋ ଅପଲୋଡ୍ କରନ୍ତୁ, Form Saathi ତାହାର ପ୍ରଶ୍ନ ପଢିବ।",
  ],
  scanButton: ["Upload photo of form", "படிவத்தின் புகைப்படத்தைப் பதிவேற்று", "फॉर्म की फ़ोटो अपलोड करें", "ଫର୍ମର ଫଟୋ ଅପଲୋଡ୍ କରନ୍ତୁ"],
  reading: ["Reading your form…", "உங்கள் படிவத்தைப் படிக்கிறேன்…", "आपका फॉर्म पढ़ रहा हूँ…", "ଆପଣଙ୍କ ଫର୍ମ ପଢୁଛି…"],
  typeAnswer: ["Type your answer", "பதிலை எழுதுங்கள்", "अपना जवाब लिखें", "ଉତ୍ତର ଲେଖନ୍ତୁ"],
  send: ["Send", "அனுப்பு", "भेजें", "ପଠାନ୍ତୁ"],
  speak: ["Speak your answer", "பதிலைப் பேசுங்கள்", "जवाब बोलें", "ଉତ୍ତର କୁହନ୍ତୁ"],
  listening: ["Listening…", "கேட்கிறேன்…", "सुन रहा हूँ…", "ଶୁଣୁଛି…"],
  largeText: ["Larger text", "பெரிய எழுத்து", "बड़े अक्षर", "ବଡ଼ ଅକ୍ଷର"],
  highContrast: ["Clearer colours", "தெளிவான நிறம்", "साफ़ रंग", "ସ୍ପଷ୍ଟ ରଙ୍ଗ"],
  readAloud: ["Read aloud", "சத்தமாகப் படி", "बोलकर सुनाएँ", "ପଢି ଶୁଣାନ୍ତୁ"],
  handsFree: ["Speak and listen", "பேசிக் கேள்", "बोलें और सुनें", "କୁହନ୍ତୁ ଓ ଶୁଣନ୍ତୁ"],
  accessibility: ["Easier to use", "எளிதாகப் பயன்படுத்த", "आसान इस्तेमाल", "ସହଜ ବ୍ୟବହାର"],
  didNotHear: [
    "I didn't hear anything. Please say your answer now.",
    "எதுவும் கேட்கவில்லை. இப்போது உங்கள் பதிலைச் சொல்லுங்கள்.",
    "मुझे कुछ सुनाई नहीं दिया। कृपया अभी अपना जवाब बोलें।",
    "ମୁଁ କିଛି ଶୁଣିପାରିଲି ନାହିଁ। ଦୟାକରି ଏବେ ଆପଣଙ୍କ ଉତ୍ତର କୁହନ୍ତୁ।",
  ],
  listenAgain: ["Listen", "கேள்", "सुनें", "ଶୁଣନ୍ତୁ"],
  speaking: ["Speaking…", "பேசுகிறேன்…", "बोल रहा हूँ…", "କହୁଛି…"],
  stop: ["Stop", "நிறுத்து", "रोकें", "ବନ୍ଦ କରନ୍ତୁ"],
  noVoice: [
    "This device has no voice for this language. On a laptop, open Form Saathi in Microsoft Edge (it has Tamil and Hindi voices). On Android, install the voice in Settings > Text-to-speech.",
    "இந்தச் சாதனத்தில் இந்த மொழிக்கான குரல் இல்லை. லேப்டாப்பில் Microsoft Edge-இல் திறக்கவும். Android-இல் Settings > Text-to-speech-இல் குரலை நிறுவவும்.",
    "इस डिवाइस में इस भाषा की आवाज़ नहीं है। लैपटॉप पर Microsoft Edge में खोलें। Android पर Settings > Text-to-speech में आवाज़ इंस्टॉल करें।",
    "ଏହି ଡିଭାଇସରେ ଏହି ଭାଷାର ସ୍ୱର ନାହିଁ। ଲାପଟପରେ Microsoft Edge ରେ ଖୋଲନ୍ତୁ। Android ରେ Settings > Text-to-speech ରେ ସ୍ୱର ଇନଷ୍ଟଲ କରନ୍ତୁ।",
  ],
  tapMic: [
    "Tap the microphone when you are ready to answer.",
    "பதில் சொல்லத் தயாரானதும் மைக்கைத் தொடுங்கள்.",
    "जवाब देने के लिए तैयार हों तो माइक दबाएँ।",
    "ଉତ୍ତର ଦେବାକୁ ପ୍ରସ୍ତୁତ ହେଲେ ମାଇକ ଦବାନ୍ତୁ।",
  ],
  explain: ["What does this mean?", "இதன் அர்த்தம் என்ன?", "इसका मतलब क्या है?", "ଏହାର ଅର୍ଥ କ'ଣ?"],
  skip: ["Skip", "தவிர்", "छोड़ें", "ଛାଡନ୍ତୁ"],
  yes: ["Yes, it's correct", "ஆம், சரி", "हाँ, सही है", "ହଁ, ଠିକ୍ ଅଛି"],
  yourForm: ["Your form", "உங்கள் படிவம்", "आपका फॉर्म", "ଆପଣଙ୍କ ଫର୍ମ"],
  progress: ["{done} of {total} answered", "{total}-இல் {done} பதில் அளிக்கப்பட்டது", "{total} में से {done} भरे गए", "{total}ରୁ {done}ଟି ଭରାହେଲା"],
  download: ["Download PDF", "PDF பதிவிறக்கு", "PDF डाउनलोड करें", "PDF ଡାଉନଲୋଡ୍ କରନ୍ତୁ"],
  downloadMasked: [
    "PDF with Aadhaar/PAN hidden",
    "ஆதார்/PAN மறைத்த PDF",
    "आधार/PAN छिपा हुआ PDF",
    "ଆଧାର/PAN ଲୁଚାଯାଇଥିବା PDF",
  ],
  finish: ["Delete my data", "என் தகவல்களை நீக்கு", "मेरा डेटा मिटाएँ", "ମୋ ତଥ୍ୟ ଡିଲିଟ୍ କରନ୍ତୁ"],
  another: ["Fill another form", "வேறு படிவம் நிரப்பு", "दूसरा फॉर्म भरें", "ଅନ୍ୟ ଫର୍ମ ଭରନ୍ତୁ"],
  documents: ["Documents to carry", "கொண்டு செல்ல வேண்டிய ஆவணங்கள்", "साथ ले जाने वाले दस्तावेज़", "ନେଇଯିବାକୁ ଥିବା ଦସ୍ତାବିଜ"],
  warnings: ["Please double-check", "மீண்டும் சரிபார்க்கவும்", "कृपया दोबारा जाँचें", "ଦୟାକରି ପୁଣି ଯାଞ୍ଚ କରନ୍ତୁ"],
  howToSubmit: ["Where to submit", "எங்கே சமர்ப்பிப்பது", "कहाँ जमा करें", "କେଉଁଠି ଜମା କରିବେ"],
  ready: ["Ready", "தயார்", "तैयार", "ପ୍ରସ୍ତୁତ"],
  optional: ["optional", "விருப்பம்", "वैकल्पिक", "ଇଚ୍ଛାଧୀନ"],
  skipped: ["skipped", "தவிர்க்கப்பட்டது", "छोड़ा गया", "ଛଡାଯାଇଛି"],
  showForm: ["See your form", "படிவத்தைப் பார்", "फॉर्म देखें", "ଫର୍ମ ଦେଖନ୍ତୁ"],
  hideForm: ["Back to chat", "உரையாடலுக்குத் திரும்பு", "बातचीत पर लौटें", "କଥାବାର୍ତ୍ତାକୁ ଫେରନ୍ତୁ"],
  sources: ["Based on", "ஆதாரம்", "आधार", "ଆଧାର"],
  privacy: [
    "Your answers are kept only while you fill the form, and deleted after 30 minutes of no activity.",
    "நீங்கள் படிவம் நிரப்பும் வரை மட்டுமே உங்கள் பதில்கள் வைக்கப்படும்; 30 நிமிடம் செயல்பாடு இல்லையெனில் நீக்கப்படும்.",
    "आपके जवाब सिर्फ़ फॉर्म भरते समय रखे जाते हैं, और 30 मिनट तक कुछ न करने पर मिटा दिए जाते हैं।",
    "ଆପଣଙ୍କ ଉତ୍ତର କେବଳ ଫର୍ମ ଭରିବା ସମୟରେ ରଖାଯାଏ, ଏବଂ 30 ମିନିଟ୍ କିଛି ନ କଲେ ଡିଲିଟ୍ ହୋଇଯାଏ।",
  ],
  expired: [
    "This session ended after 30 minutes without activity, so your answers were deleted. Start the form again.",
    "30 நிமிடம் செயல்பாடு இல்லாததால் இந்த அமர்வு முடிந்தது, உங்கள் பதில்கள் நீக்கப்பட்டன. படிவத்தை மீண்டும் தொடங்குங்கள்.",
    "30 मिनट तक कुछ न करने से यह सत्र खत्म हो गया और आपके जवाब मिटा दिए गए। फॉर्म फिर से शुरू करें।",
    "30 ମିନିଟ୍ କିଛି ନ କରିବାରୁ ଏହି ସେସନ୍ ଶେଷ ହେଲା ଏବଂ ଆପଣଙ୍କ ଉତ୍ତର ଡିଲିଟ୍ ହେଲା। ଫର୍ମ ପୁଣି ଆରମ୍ଭ କରନ୍ତୁ।",
  ],
  network: [
    "Can't reach the Form Saathi server. Check that the backend is running on port 8000, then try again.",
    "Form Saathi சர்வருடன் இணைக்க முடியவில்லை. பின்னணி சேவை port 8000-இல் இயங்குகிறதா என்று பார்த்து மீண்டும் முயலுங்கள்.",
    "Form Saathi सर्वर से जुड़ नहीं पा रहे। देखें कि बैकएंड port 8000 पर चल रहा है, फिर दोबारा कोशिश करें।",
    "Form Saathi ସର୍ଭର ସହ ଯୋଡି ହେଉନାହିଁ। ବ୍ୟାକଏଣ୍ଡ port 8000 ରେ ଚାଲୁଛି କି ଦେଖନ୍ତୁ, ତାପରେ ପୁଣି ଚେଷ୍ଟା କରନ୍ତୁ।",
  ],
  bank: ["Bank", "வங்கி", "बैंक", "ବ୍ୟାଙ୍କ"],
  utilities: ["Electricity, water and gas", "மின்சாரம், குடிநீர், எரிவாயு", "बिजली, पानी और गैस", "ବିଦ୍ୟୁତ୍, ପାଣି ଓ ଗ୍ୟାସ"],
  property: ["Property and rent", "சொத்து மற்றும் வாடகை", "संपत्ति और किराया", "ସମ୍ପତ୍ତି ଓ ଭଡା"],
  tax: ["Tax", "வரி", "टैक्स", "ଟିକସ"],
  employment: ["Jobs and PF", "வேலை மற்றும் PF", "नौकरी और PF", "ଚାକିରି ଓ PF"],
  transport: ["Vehicles", "வாகனங்கள்", "वाहन", "ଯାନ"],
  custom: ["From your photo", "உங்கள் புகைப்படத்திலிருந்து", "आपकी फ़ोटो से", "ଆପଣଙ୍କ ଫଟୋରୁ"],
};

const IDX: Record<Lang, number> = { en: 0, ta: 1, hi: 2, or: 3 };

export function t(key: string, lang: Lang, vars: Record<string, string | number> = {}): string {
  const row = S[key];
  if (!row) return key;
  let out = row[IDX[lang]] || row[0];
  for (const [k, v] of Object.entries(vars)) out = out.replace(`{${k}}`, String(v));
  return out;
}
