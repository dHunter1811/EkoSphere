from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('role',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Loop melalui semua field di form
        for field_name, field in self.fields.items():
            # Beri kelas 'form-control' untuk semua input teks dan password
            if isinstance(field.widget, (forms.TextInput, forms.PasswordInput)):
                field.widget.attrs.update({'class': 'form-control'})
            # Beri kelas 'form-select' untuk dropdown
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})