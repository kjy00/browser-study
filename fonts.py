import skia

FONTS = {}

def get_font(size, weight, style):
    # 글꼴 데이터는 Typeface에 있고, Font는 그 글꼴의 크기만 정한다.
    key = (weight, style)
    if key not in FONTS:
        if weight == "bold":
            skia_weight = skia.FontStyle.kBold_Weight
        else:
            skia_weight = skia.FontStyle.kNormal_Weight
        if style == "italic":
            skia_style = skia.FontStyle.kItalic_Slant
        else:
            skia_style = skia.FontStyle.kUpright_Slant
        skia_width = skia.FontStyle.kNormal_Width
        style_info = skia.FontStyle(skia_weight, skia_width, skia_style)
        font = skia.Typeface("Arial", style_info)
        FONTS[key] = font
    return skia.Font(FONTS[key], size)

def linespace(font):
    # Skia의 ascent는 위로 갈수록 음수다. 줄 높이는 descent에서 ascent를 빼면 된다.
    metrics = font.getMetrics()
    return metrics.fDescent - metrics.fAscent
