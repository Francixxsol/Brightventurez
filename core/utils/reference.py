import uuid

def generate_reference():
    return uuid.uuid4().hex[:12].upper()
