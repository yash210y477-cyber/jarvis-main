"""Turn a reply into something a speech engine can actually pronounce.

Three problems this fixes:

* Markdown leaks into the voice (`**bold**`, backticks, bullets, links), and the
  engine reads the leftover symbols out loud.
* Hinglish written in Latin letters is read as English words — "aaj" comes out
  letter by letter. It is transliterated to Devanagari so a Hindi voice says it.
* One voice cannot do both languages, so the text is split by script and each
  part is spoken by a matching voice.
"""

import re

DEVANAGARI = re.compile(r"[\u0900-\u097F]")
LATIN = re.compile(r"[A-Za-z]")

URL = re.compile(r"https?://\S+|www\.\S+")
CODE = re.compile(r"```[\s\S]*?```")
INLINE_CODE = re.compile(r"`([^`]*)`")
IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
MARKDOWN_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F]")
DECORATION = re.compile(r"[*_#>|~^=<>\[\]{}()\\/]+")

# Words the rules below would mangle, plus the everyday ones worth getting right.
WORDS = {
    "aaj": "आज", "kal": "कल", "abhi": "अभी", "phir": "फिर", "fir": "फिर",
    "hai": "है", "hain": "हैं", "hoon": "हूँ", "hu": "हूँ", "ho": "हो",
    "tha": "था", "thi": "थी", "the": "थे", "hoga": "होगा", "hogi": "होगी",
    "kya": "क्या", "kyun": "क्यों", "kyu": "क्यों", "kaise": "कैसे", "kaisa": "कैसा",
    "kaisi": "कैसी", "kahan": "कहाँ", "kab": "कब", "kitna": "कितना", "kitne": "कितने",
    "kaun": "कौन", "kaunsa": "कौनसा", "main": "मैं", "mein": "में", "mai": "मैं",
    "mujhe": "मुझे", "mera": "मेरा", "meri": "मेरी", "mere": "मेरे",
    "tum": "तुम", "tumhara": "तुम्हारा", "aap": "आप", "aapka": "आपका", "aapki": "आपकी",
    "hum": "हम", "hamara": "हमारा", "uska": "उसका", "uski": "उसकी", "woh": "वो", "wo": "वो",
    "yeh": "यह", "ye": "ये", "yeah": "ये", "iska": "इसका", "inki": "इनकी",
    "nahi": "नहीं", "nahin": "नहीं", "haan": "हाँ", "han": "हाँ", "ji": "जी",
    "karo": "करो", "karna": "करना", "kar": "कर", "kiya": "किया", "karta": "करता",
    "karti": "करती", "karne": "करने", "karke": "करके", "batao": "बताओ", "bata": "बता",
    "bataiye": "बताइए", "bolo": "बोलो", "suno": "सुनो", "dekho": "देखो",
    "chalo": "चलो", "chal": "चल", "bhejo": "भेजो", "bhej": "भेज", "kholo": "खोलो",
    "band": "बंद", "chalu": "चालू", "theek": "ठीक", "thik": "ठीक", "accha": "अच्छा",
    "acha": "अच्छा", "bahut": "बहुत", "zyada": "ज़्यादा", "jyada": "ज़्यादा",
    "thoda": "थोड़ा", "kuch": "कुछ", "sab": "सब", "sabhi": "सभी", "aur": "और",
    "lekin": "लेकिन", "magar": "मगर", "kyunki": "क्योंकि", "isliye": "इसलिए",
    "ko": "को", "ka": "का", "ki": "की", "ke": "के", "se": "से", "par": "पर",
    "tak": "तक", "me": "में", "bhi": "भी", "hi": "ही", "sirf": "सिर्फ",
    "yaar": "यार", "bhai": "भाई", "dost": "दोस्त", "mummy": "मम्मी", "papa": "पापा",
    "party": "पार्टी", "message": "मैसेज", "photo": "फोटो", "screenshot": "स्क्रीनशॉट",
    "jarvis": "जार्विस", "yash": "यश", "samay": "समय", "time": "टाइम",
    "din": "दिन", "raat": "रात", "subah": "सुबह", "shaam": "शाम", "baje": "बजे",
    "kaam": "काम", "baat": "बात", "cheez": "चीज़", "log": "लोग", "ghar": "घर",
    "paisa": "पैसा", "pani": "पानी", "khana": "खाना", "wala": "वाला", "wali": "वाली",
    "gaya": "गया", "gayi": "गई", "raha": "रहा", "rahi": "रही", "rahe": "रहे",
    "sakta": "सकता", "sakti": "सकती", "chahiye": "चाहिए", "milta": "मिलता",
    "samajh": "समझ", "yaad": "याद", "dil": "दिल", "bada": "बड़ा", "chhota": "छोटा",
    "naya": "नया", "purana": "पुराना", "pehle": "पहले", "baad": "बाद",
    "yahan": "यहाँ", "wahan": "वहाँ", "udhar": "उधर", "idhar": "इधर",
    "khol": "खोल", "chalao": "चलाओ", "bajao": "बजाओ", "dikhao": "दिखाओ",
    "shukriya": "शुक्रिया", "dhanyawad": "धन्यवाद", "namaste": "नमस्ते",
    "help": "मदद", "problem": "समस्या", "jawab": "जवाब", "sawal": "सवाल",
}

CONSONANTS = [
    ("chh", "छ"), ("ch", "च"), ("kh", "ख"), ("gh", "घ"), ("jh", "झ"),
    ("th", "थ"), ("dh", "ध"), ("ph", "फ"), ("bh", "भ"), ("sh", "श"),
    ("gn", "ज्ञ"), ("ks", "क्ष"), ("tr", "त्र"), ("kr", "क्र"),
    ("k", "क"), ("g", "ग"), ("j", "ज"), ("t", "त"), ("d", "द"), ("n", "न"),
    ("p", "प"), ("b", "ब"), ("m", "म"), ("y", "य"), ("r", "र"), ("l", "ल"),
    ("v", "व"), ("w", "व"), ("s", "स"), ("h", "ह"), ("f", "फ़"), ("z", "ज़"),
    ("q", "क"), ("x", "क्स"), ("c", "क"),
]

VOWEL_SOUNDS = [
    ("aa", "आ", "ा"), ("ai", "ऐ", "ै"), ("au", "औ", "ौ"), ("ee", "ई", "ी"),
    ("ii", "ई", "ी"), ("oo", "ऊ", "ू"), ("uu", "ऊ", "ू"), ("ou", "औ", "ौ"),
    ("a", "अ", ""), ("i", "इ", "ि"), ("u", "उ", "ु"), ("e", "ए", "े"),
    ("o", "ओ", "ो"),
]


def clean(text: str) -> str:
    """Strip everything a voice would otherwise read out loud."""

    text = CODE.sub(" ", text or "")
    text = IMAGE.sub(" ", text)
    text = MARKDOWN_LINK.sub(r"\1", text)
    text = URL.sub(" ", text)
    text = INLINE_CODE.sub(r"\1", text)
    text = EMOJI.sub(" ", text)
    text = DECORATION.sub(" ", text)
    text = text.replace("&", " and ").replace("%", " percent ")
    # A question mark is spoken by some voices; a full stop keeps the pause.
    text = text.replace("?", ".").replace("!", ".")
    text = re.sub(r"\.{2,}", ".", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)

    return text.strip(" .\n") or ""


def _word_to_devanagari(word: str) -> str:
    lowered = word.lower()
    known = WORDS.get(lowered)

    if known:
        return known

    out = []
    index = 0

    while index < len(lowered):
        char = lowered[index]

        if not char.isalpha():
            out.append(char)
            index += 1
            continue

        consonant = next(
            (pair for pair in CONSONANTS if lowered.startswith(pair[0], index)), None
        )

        if consonant:
            out.append(consonant[1])
            index += len(consonant[0])

            vowel = next(
                (item for item in VOWEL_SOUNDS if lowered.startswith(item[0], index)),
                None,
            )

            if vowel:
                out.append(vowel[2])
                index += len(vowel[0])
            elif index >= len(lowered) or not lowered[index].isalpha():
                out.append("")
            else:
                out.append("")

            continue

        vowel = next(
            (item for item in VOWEL_SOUNDS if lowered.startswith(item[0], index)), None
        )

        if vowel:
            out.append(vowel[1])
            index += len(vowel[0])
            continue

        out.append(char)
        index += 1

    return "".join(out)


def to_devanagari(text: str) -> str:
    """Hinglish in Latin letters, written in Devanagari so Hindi voices say it."""

    return re.sub(
        r"[A-Za-z]+",
        lambda match: _word_to_devanagari(match.group(0)),
        text,
    )


LATIN_VOWELS = {
    "अ": "a", "आ": "aa", "इ": "i", "ई": "i", "उ": "u", "ऊ": "u",
    "ऋ": "ri", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au",
}

LATIN_CONSONANTS = {
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "n", "च": "ch",
    "छ": "chh", "ज": "j", "झ": "jh", "ञ": "n", "ट": "t", "ठ": "th",
    "ड": "d", "ढ": "dh", "ण": "n", "त": "t", "थ": "th", "द": "d",
    "ध": "dh", "न": "n", "प": "p", "फ": "ph", "ब": "b", "भ": "bh",
    "म": "m", "य": "y", "र": "r", "ल": "l", "व": "v", "श": "sh",
    "ष": "sh", "स": "s", "ह": "h", "ळ": "l", "क़": "q", "ख़": "kh",
    "ग़": "g", "ज़": "z", "ड़": "r", "ढ़": "rh", "फ़": "f", "य़": "y",
}

LATIN_MATRAS = {
    "ा": "aa", "ि": "i", "ी": "i", "ु": "u", "ू": "u", "ृ": "ri",
    "े": "e", "ै": "ai", "ो": "o", "ौ": "au", "ॉ": "o", "ॅ": "e",
}

ANUSVARA = {"ं": "n", "ँ": "n", "ः": "h", "़": ""}


def to_hinglish(text: str) -> str:
    """Devanagari speech written the way Hinglish is typed in chat."""

    out = []
    index = 0

    while index < len(text):
        char = text[index]

        if char in LATIN_CONSONANTS:
            out.append(LATIN_CONSONANTS[char])
            index += 1

            if index < len(text) and text[index] in LATIN_MATRAS:
                out.append(LATIN_MATRAS[text[index]])
                index += 1
            elif index < len(text) and text[index] == "्":
                # Halant joins the next consonant: no vowel in between.
                index += 1
            elif index < len(text) and text[index] in ANUSVARA:
                out.append("a" + ANUSVARA[text[index]])
                index += 1
            elif index < len(text) and (
                text[index] in LATIN_CONSONANTS or text[index] in LATIN_VOWELS
            ):
                # No mark after the consonant: the inherent "a" is spoken.
                out.append("a")

            continue

        if char in LATIN_VOWELS:
            out.append(LATIN_VOWELS[char])
            index += 1
            continue

        if char in ANUSVARA:
            out.append(ANUSVARA[char])
            index += 1
            continue

        out.append(char)
        index += 1

    written = "".join(out)

    # "gaanaa" / "bajaao" are spelled the way people type them ("gana",
    # "bajao"), but a doubled vowel at the start of a word is real ("aaj").
    words = [
        word[:1] + re.sub(r"([aiueo])\1+", r"\1", word[1:])
        for word in written.split()
    ]

    return " ".join(words)


def is_hinglish(text: str) -> bool:
    """Latin text that is really Hindi written in English letters."""

    from brain.language import is_hinglish as detect

    return detect(text)


def plan(text: str, voice: str, male: str, female: str) -> list[tuple[str, str]]:
    """Split a reply into (voice, text) pieces: Hindi for Hindi, the rest as is."""

    text = clean(text)

    if not text:
        return []

    hindi = male if _is_male(voice) else female

    if DEVANAGARI.search(text):
        return [(hindi, text)]

    if LATIN.search(text) and is_hinglish(text):
        spoken = to_devanagari(text)

        if DEVANAGARI.search(spoken):
            return [(hindi, spoken)]

    return [(voice, text)]


MALE_VOICES = {
    "en-IN-PrabhatNeural",
    "en-US-AndrewNeural",
    "en-US-AndrewMultilingualNeural",
    "en-GB-RyanNeural",
    "en-US-GuyNeural",
    "hi-IN-MadhurNeural",
}

HINDI_MALE = "hi-IN-MadhurNeural"
HINDI_FEMALE = "hi-IN-SwaraNeural"


def _is_male(voice: str) -> bool:
    return voice in MALE_VOICES or "Madhur" in voice
