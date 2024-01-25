# Vector Indexes

Vector Indexes are a feature of Wagtail Vector Index that allows you to query site content using AI tools. They provide a way to turn Django models, Wagtail pages, and anything else in to embeddings which are stored in your database (and optionally in another Vector Database), and then query that content using natural language.

A barebones implementation of `VectorIndex` needs to implement one method; `get_documents` - this returns an Iterable of `Document` objects, which represent an embedding along with some metadata.

There are two ways to use Vector Indexes. Either:

-   Adding the `PageVectorIndexedMixin` to a Wagtail Page model, or the `VectorIndexedMixin` to a plain Django model, which will automatically generate an Index for that model.
-   Creating your own subclass of one of the `VectorIndex` classes.

## Automatically Generating Indexes using `PageVectorIndexedMixin` or `VectorIndexedMixin`

To generate a Vector Index based on an existing model in your application:

1. Add Wagtail AI's `PageVectorIndexedMixin` or `VectorIndexedMixin` mixin to your model.
2. Set `embedding_fields` to a list of `EmbeddingField`s representing the fields you want to be included in the embeddings.

```python
from django.db import models
from wagtail.models import Page
from wagtail_vector_index.index import PageVectorIndexedMixin, EmbeddingField


class MyPage(PageVectorIndexedMixin, Page):
    body = models.TextField()

    embedding_fields = [EmbeddingField("title"), EmbeddingField("body")]
```

You'll then be able to call the `get_vector_index()` classmethod on your model to get the generated `ModelVectorIndex`.

```python
index = MyPage.get_vector_index()
```


## Indexing across models

If you want to be able to query across multiple models, or on a subset of models, they need to be in a vector index together.

To do this, you can define and register your own `ModelVectorIndex`:

```python
from wagtail_vector_index.index import ModelVectorIndex


class MyModelVectorIndex(ModelVectorIndex):
    querysets = [
        MyModel.objects.all(),
        MyOtherModel.objects.filter(name__startswith="AI: "),
    ]
```

Once populated (with the `update_vector_indexes` management command), this can be queried just like an automatically generated index:

```python
index = MyModelVectorIndex()
index.query("Are you suggesting that coconuts migrate?")
```

## Customising embedding splits

Due to token limitations in AI models, content from indexed models is split up in to chunks, with embeddings generated separately.

By default this is done by merging all `embedding_fields` together and then splitting on new paragraphs, new lines, sentences and words (getting more specific as required) until it fits within a defined split size.

To customise this behaviour, override the `_get_split_content` method on a `VectorIndexedMixin` model.

```python
def _get_split_content(
    self, *, split_length: int = 800, split_overlap: int = 100
) -> List[str]:
    return ["What? A swallow carrying a coconut?"]
```

It is up to your implementation to respect the requested `split_length` and `split_overlap`.
