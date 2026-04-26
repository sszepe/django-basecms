from django import forms
from .models import CMSPage, MediaAsset, NavbarItem, PageBlock

class CMSPageAdminForm(forms.ModelForm):
    class Meta:
        model = CMSPage
        fields = "__all__"

class NavbarItemAdminForm(forms.ModelForm):
    class Meta:
        model = NavbarItem
        fields = "__all__"

class PageBlockAdminForm(forms.ModelForm):
    class Meta:
        model = PageBlock
        fields = "__all__"

class MediaAssetAdminForm(forms.ModelForm):
    class Meta:
        model = MediaAsset
        fields = "__all__"
