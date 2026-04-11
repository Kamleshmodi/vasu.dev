from django import forms

from .models import ProductRating


class ProductRatingForm(forms.ModelForm):
    class Meta:
        model = ProductRating
        fields = ['rating', 'title', 'review', 'review_image']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'review-input', 'placeholder': 'Short title for your review'}),
            'review': forms.Textarea(
                attrs={
                    'class': 'review-textarea',
                    'placeholder': 'Share what you liked about the product, fit, quality, or delivery experience.',
                    'rows': 5,
                }
            ),
            'review_image': forms.ClearableFileInput(
                attrs={
                    'class': 'review-file-input',
                    'accept': 'image/*',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rating'].choices = [(value, f'{value} Star') for value in range(5, 0, -1)]
        self.fields['rating'].widget = forms.RadioSelect()
        self.fields['rating'].required = True
        self.fields['title'].required = False
        self.fields['review'].required = False
        self.fields['review_image'].required = False

    def clean_review_image(self):
        image = self.cleaned_data.get('review_image')
        if not image:
            return image

        max_size = 5 * 1024 * 1024
        if image.size > max_size:
            raise forms.ValidationError('Review image size must be 5 MB or smaller.')

        content_type = getattr(image, 'content_type', '') or ''
        if content_type and not content_type.startswith('image/'):
            raise forms.ValidationError('Only image files are allowed for review uploads.')

        return image
