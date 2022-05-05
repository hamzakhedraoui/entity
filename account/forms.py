from django import forms
from .models import Account,LogIn

class AccountForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class':'form-control',}))
    userName = forms.CharField(widget=forms.TextInput(attrs={'class':'form-control',}))
    email = forms.EmailField(widget=forms.TextInput(attrs={'class':'form-control',}))
    class Meta:
        model = Account
        fields = ['userName','email','password']

class LoginForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class':'form-control',}))
    email = forms.EmailField(widget=forms.TextInput(attrs={'class':'form-control',}))
    class Meta:
        model = LogIn
        fields = ['email','password']