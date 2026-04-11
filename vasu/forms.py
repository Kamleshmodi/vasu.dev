from django import forms
from appaccounts.models import Account
from aapstore.models import UserProfile 
from .address_utils import (
    DELIVERY_COUNTRY,
    get_address_options,
    get_delivery_country_choices,
    normalize_location_name,
    validate_delivery_address,
)

# forms.py

class UserForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ('username', 'email')

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'
            self.fields[field].widget.attrs['placeholder'] = f'Enter {field.replace("_", " ")}'

class UserProfileForm(forms.ModelForm):
    profile_picture = forms.ImageField(required=False, error_messages = {'invalid':("Image files only")}, widget=forms.FileInput)
    country = forms.ChoiceField(choices=(), required=False)
    state = forms.ChoiceField(choices=(), required=False)
    district = forms.ChoiceField(choices=(), required=False)
    city = forms.ChoiceField(choices=(), required=False)

    class Meta:
        model = UserProfile
        fields = (
            'profile_picture',
            'address_line_1',
            'address_line_2',
            'country',
            'state',
            'district',
            'city',
            'postal_code',
        )

    def __init__(self, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)
        bound_data = self.data if self.is_bound else {}
        selected_country = normalize_location_name(
            bound_data.get(self.add_prefix('country'))
            or self.initial.get('country')
            or getattr(self.instance, 'country', '')
            or DELIVERY_COUNTRY
        )
        selected_state = normalize_location_name(
            bound_data.get(self.add_prefix('state'))
            or self.initial.get('state')
            or getattr(self.instance, 'state', '')
        )
        selected_district = normalize_location_name(
            bound_data.get(self.add_prefix('district'))
            or self.initial.get('district')
            or getattr(self.instance, 'district', '')
        )
        selected_city = normalize_location_name(
            bound_data.get(self.add_prefix('city'))
            or self.initial.get('city')
            or getattr(self.instance, 'city', '')
        )

        address_options = get_address_options(selected_country, selected_state)
        self.fields['country'].choices = get_delivery_country_choices()
        self.fields['state'].choices = [('', 'Select State')] + [(item, item) for item in address_options['states']]
        self.fields['district'].choices = [('', 'Select District')] + [(item, item) for item in address_options['districts']]
        self.fields['city'].choices = [('', 'Select City')] + [(item, item) for item in address_options['cities']]

        select_fields = {'country', 'state', 'district', 'city'}
        for field in self.fields:
            css_class = 'form-select' if field in select_fields else 'form-control'
            self.fields[field].widget.attrs['class'] = css_class
            if field not in select_fields:
                self.fields[field].widget.attrs['placeholder'] = f'Enter {field.replace("_", " ")}'

        self.fields['country'].initial = selected_country
        self.fields['state'].initial = selected_state
        self.fields['district'].initial = selected_district
        self.fields['city'].initial = selected_city

        self.fields['country'].widget.attrs.update({'data-address-role': 'country'})
        self.fields['state'].widget.attrs.update({'data-address-role': 'state'})
        self.fields['district'].widget.attrs.update({'data-address-role': 'district'})
        self.fields['city'].widget.attrs.update({'data-address-role': 'city'})
        self.fields['postal_code'].widget.attrs.update({'data-address-role': 'postal-code', 'maxlength': 6})

    def clean(self):
        cleaned_data = super().clean()
        address_line_1 = normalize_location_name(cleaned_data.get('address_line_1'))
        country = normalize_location_name(cleaned_data.get('country'))
        state = normalize_location_name(cleaned_data.get('state'))
        district = normalize_location_name(cleaned_data.get('district'))
        city = normalize_location_name(cleaned_data.get('city'))
        postal_code = normalize_location_name(cleaned_data.get('postal_code'))

        has_any_address = any((address_line_1, country, state, district, city, postal_code))
        if not has_any_address:
            return cleaned_data

        required_fields = {
            'address_line_1': 'Please enter address line 1.',
            'country': 'Please choose your delivery country.',
            'state': 'Please choose your state.',
            'district': 'Please choose your district.',
            'city': 'Please choose your city.',
            'postal_code': 'Please enter your PIN code.',
        }
        for field_name, message in required_fields.items():
            if not normalize_location_name(cleaned_data.get(field_name)):
                self.add_error(field_name, message)

        if self.errors:
            return cleaned_data

        is_valid, validation_message = validate_delivery_address(
            country=country,
            state=state,
            district=district,
            city=city,
            postal_code=postal_code,
        )
        if not is_valid:
            self.add_error('postal_code', validation_message)

        return cleaned_data
