"""Prueba directa (sin servidor) de estimar_tallas() cruzando altura+peso."""
from app import estimar_tallas

casos = [
    ("Mujer", "62kg", "1.63m"),   # peso->M(60-70), altura->S(hasta 1.65) => principal S, otra M
    ("Mujer", "55kg", "1.63m"),   # peso->S, altura->S => empatan, vecina M
    ("Mujer", "90kg", "1.80m"),   # peso->XL, altura->XL => empatan, vecina L
    ("Hombre", "75kg", "1.72m"),  # peso->M(68-80), altura->M(1.70-1.78) => empatan
    ("Hombre", "65kg", "1.90m"),  # peso->S, altura->XL => principal S, otra XL
    ("Hombre", "", "1.72m"),      # solo altura
    ("Mujer", "62kg", ""),        # solo peso
    ("Unisex", "", ""),           # sin datos
]

for genero, peso, altura in casos:
    print(f"{genero:8} peso={peso or '-':6} altura={altura or '-':6} -> {estimar_tallas(genero, peso, altura)}")
