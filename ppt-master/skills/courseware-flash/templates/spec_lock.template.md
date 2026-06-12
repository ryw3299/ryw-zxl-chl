## canvas
- viewBox: {{ canvas.viewBox }}
- format: {{ canvas.format }}

## colors
{% for k, v in colors.items() %}- {{ k }}: {{ v }}
{% endfor %}

## typography
{% for k, v in typography.items() %}- {{ k }}: {{ v }}
{% endfor %}

## icons
- library: {{ icons.library }}
- inventory: {{ icons.inventory | join(', ') }}

## page_rhythm
{% for slide in slides %}- {{ '%02d' % slide.slide_id }}: {{ slide.rhythm }}
{% endfor %}

## forbidden
- Mixing icon libraries
- rgba()
- <style>, class, <foreignObject>, textPath, @font-face, <animate*>, <script>, <iframe>, <symbol>+<use>
- <g opacity> (set opacity on each child element individually)
- HTML named entities in text
