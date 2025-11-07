from django import forms
from django.contrib.auth.models import User
from .models import SellRequest  # ✅ Correct model import


class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password2 = cleaned_data.get("password2")
        if password != password2:
            raise forms.ValidationError("Passwords do not match")
        return cleaned_data


class SellDataRequestForm(forms.ModelForm):
    class Meta:
        model = SellRequest  # ✅ changed from DataTransaction
        fields = ["network", "amount", "phone_number"]  # ✅ match SellRequest fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["network"].widget.attrs.update({"class": "form-control"})
        self.fields["amount"].widget.attrs.update({"class": "form-control"})
        self.fields["phone_number"].widget.attrs.update({"class": "form-control"})
