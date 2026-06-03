from django import forms
from .models import Review


class ReviewForm(forms.ModelForm):
    """Customer review submission form."""

    class Meta:
        model = Review
        fields = [
            'title', 'comment',
            'overall_rating', 'food_rating', 'service_rating',
            'ambience_rating', 'value_rating',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'tm-input',
                'placeholder': 'Give your review a title',
            }),
            'comment': forms.Textarea(attrs={
                'class': 'tm-textarea',
                'placeholder': 'Share your dining experience…',
                'rows': 5,
                'data-max-chars': '1500',
            }),
            'overall_rating': forms.HiddenInput(),
            'food_rating':     forms.HiddenInput(),
            'service_rating':  forms.HiddenInput(),
            'ambience_rating': forms.HiddenInput(),
            'value_rating':    forms.HiddenInput(),
        }

    def clean(self):
        cleaned = super().clean()
        for field in ['overall_rating', 'food_rating', 'service_rating', 'ambience_rating', 'value_rating']:
            val = cleaned.get(field)
            if val is not None and not (1 <= int(val) <= 5):
                self.add_error(field, 'Rating must be between 1 and 5.')
        return cleaned
