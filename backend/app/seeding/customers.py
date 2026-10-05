from faker import Faker

_fake = Faker()


def generate_customer() -> dict:
    return {
        "email_address": _fake.unique.email(),
        "full_name": _fake.name(),
    }
