import factory
import wagtail_factories
from faker import Faker
from testapp.models import DifferentPage, ExamplePage
from wagtail_vector_index.models import Embedding

fake = Faker()


class ExamplePageFactory(wagtail_factories.PageFactory):
    class Meta:
        model = ExamplePage

    title = factory.Faker("sentence")
    body = factory.LazyFunction(lambda: "\n".join(fake.paragraphs()))


class DifferentPageFactory(wagtail_factories.PageFactory):
    class Meta:
        model = DifferentPage

    body = factory.LazyFunction(lambda: "\n".join(fake.paragraphs()))


class EmbeddingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Embedding

    vector = factory.LazyFunction(lambda: [fake.pyfloat() for _ in range(300)])
    content = factory.LazyFunction(lambda: "\n".join(fake.paragraphs()))
