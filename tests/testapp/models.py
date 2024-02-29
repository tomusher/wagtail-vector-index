from django.db import models
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page
from wagtail_vector_index.index.model import (
    PageVectorIndex,
)
from wagtail_vector_index.index.registry import registry
from wagtail_vector_index.models import EmbeddingField, VectorIndexedMixin


class ExampleModel(VectorIndexedMixin, models.Model):
    title = models.CharField(max_length=255)
    body = models.TextField()

    embedding_fields = [EmbeddingField("title", important=True), EmbeddingField("body")]

    def __str__(self):
        return self.title


class ExamplePage(VectorIndexedMixin, Page):
    body = RichTextField()

    content_panels = [*Page.content_panels, FieldPanel("body")]

    embedding_fields = [EmbeddingField("title", important=True), EmbeddingField("body")]


class DifferentPage(VectorIndexedMixin, Page):
    body = RichTextField()

    content_panels = [*Page.content_panels, FieldPanel("body")]

    embedding_fields = [EmbeddingField("title", important=True), EmbeddingField("body")]


class MultiplePageVectorIndex(PageVectorIndex):
    querysets = [ExamplePage.objects.all(), DifferentPage.objects.all()]  # type: ignore


registry.register_index(MultiplePageVectorIndex())
