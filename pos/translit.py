# pos/translit.py
import re

def latin_to_cyrillic(text):
    if not text:
        return ""
    replacements = [
        ("Ch", "Ч"), ("CH", "Ч"), ("ch", "ч"),
        ("Sh", "Ш"), ("SH", "Ш"), ("sh", "ш"),
        ("Yo", "Ё"), ("YO", "Ё"), ("yo", "ё"),
        ("Yu", "Ю"), ("YU", "Ю"), ("yu", "ю"),
        ("Ya", "Я"), ("YA", "Я"), ("ya", "я"),
        ("Ye", "Е"), ("YE", "Е"), ("ye", "е"),
        ("O'", "Ў"), ("O’", "Ў"), ("O‘", "Ў"), ("O`", "Ў"),
        ("o'", "ў"), ("o’", "ў"), ("o‘", "ў"), ("o`", "ў"),
        ("G'", "Ғ"), ("G’", "Ғ"), ("G‘", "Ғ"), ("G`", "Ғ"),
        ("g'", "ғ"), ("g’", "ғ"), ("g‘", "ғ"), ("g`", "ғ"),
        ("A", "А"), ("a", "а"), ("B", "Б"), ("b", "б"),
        ("V", "В"), ("v", "в"), ("G", "Г"), ("g", "г"),
        ("D", "Д"), ("d", "д"), ("E", "Е"), ("e", "е"),
        ("Z", "З"), ("z", "з"), ("I", "И"), ("i", "и"),
        ("Y", "Й"), ("y", "й"), ("K", "К"), ("k", "к"),
        ("L", "Л"), ("l", "л"), ("M", "М"), ("m", "м"),
        ("N", "Н"), ("n", "н"), ("O", "О"), ("o", "о"),
        ("P", "П"), ("p", "п"), ("R", "Р"), ("r", "р"), # <- R to'g'rilandi
        ("S", "С"), ("s", "с"), ("T", "Т"), ("t", "т"),
        ("U", "У"), ("u", "у"), ("F", "Ф"), ("f", "ф"),
        ("X", "Х"), ("x", "х"), ("Q", "Қ"), ("q", "қ"),
        ("H", "Ҳ"), ("h", "ҳ"), ("J", "Ж"), ("j", "ж"),
        ("Ts", "Ц"), ("ts", "ц"), ("TS", "Ц"),
    ]
    for lat, cyr in replacements:
        text = text.replace(lat, cyr)
    return text

def cyrillic_to_latin(text):
    if not text:
        return ""
    replacements = [
        ("Ч", "Ch"), ("ч", "ch"),
        ("Ш", "Sh"), ("ш", "sh"),
        ("Ё", "Yo"), ("ё", "yo"),
        ("Ю", "Yu"), ("ю", "yu"),
        ("Я", "Ya"), ("я", "ya"),
        ("Ў", "O'"), ("ў", "o'"),
        ("Ғ", "G'"), ("ғ", "g'"),
        ("Ц", "Ts"), ("ц", "ts"),
        ("А", "A"), ("а", "a"),
        ("Б", "B"), ("б", "b"),
        ("В", "V"), ("в", "v"),
        ("Г", "G"), ("г", "g"),
        ("Д", "D"), ("д", "d"),
        ("Е", "E"), ("е", "e"),
        ("Ж", "J"), ("ж", "j"),
        ("З", "Z"), ("з", "z"),
        ("И", "I"), ("и", "i"),
        ("Й", "Y"), ("й", "y"),
        ("К", "K"), ("к", "k"),
        ("Л", "L"), ("л", "l"),
        ("М", "M"), ("м", "m"),
        ("Н", "N"), ("n", "n"),
        ("О", "O"), ("о", "o"),
        ("П", "P"), ("п", "p"),
        ("Р", "R"), ("р", "r"),
        ("С", "S"), ("с", "s"),
        ("Т", "T"), ("т", "t"),
        ("У", "U"), ("у", "u"),
        ("Ф", "F"), ("ф", "f"),
        ("Х", "X"), ("х", "x"),
        ("Қ", "Q"), ("қ", "q"),
        ("Ҳ", "H"), ("ҳ", "h"),
        ("Э", "E"), ("э", "e"),
    ]
    for cyr, lat in replacements:
        text = text.replace(cyr, lat)
    return text

def convert_html_to_cyrillic(html_content):
    tokens = re.split(r'(<[^>]+>)', html_content)
    in_script, in_style = False, False
    for i in range(len(tokens)):
        token = tokens[i]
        if token.startswith('<'):
            lower_token = token.lower()
            if '<script' in lower_token: in_script = True
            elif '</script' in lower_token: in_script = False
            elif '<style' in lower_token: in_style = True
            elif '</style' in lower_token: in_style = False
        else:
            if not in_script and not in_style:
                tokens[i] = latin_to_cyrillic(token)
    return ''.join(tokens)