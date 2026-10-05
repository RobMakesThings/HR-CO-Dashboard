from faker import Faker

_fake = Faker()
_WORDS = [
    "Keyboard", "Monitor", "Mouse", "Charger", "Cable", "Hub", "Webcam",
    "Speaker", "Headset", "Microphone", "Stand", "Dock", "Adapter", "Router",
    "Scanner", "Printer",
]


def generate_product() -> dict:
    return {
        "product_name": f"{_fake.random.choice(_WORDS)} {_fake.random_int(1000, 9999)}",
        "unit_price": round(_fake.random.uniform(5, 900), 2),
    }
