from django.test import SimpleTestCase
from finances.domain.entities.filtering.type_validation import (
    TypeVariant,
    IntTypeValidator,
    FloatTypeValidator,
    BooleanTypeValidator,
    DatetimeTypeValidator,
    UUIDTypeValidator,
    TypeValidatorBuilder
)


class TypeValidationTests(SimpleTestCase):
    def test_int_validator(self):
        self.assertTrue(IntTypeValidator("123").validate())
        self.assertTrue(IntTypeValidator("-123").validate())
        self.assertTrue(IntTypeValidator("+123").validate())
        self.assertFalse(IntTypeValidator("12.3").validate())
        self.assertFalse(IntTypeValidator("abc").validate())

    def test_float_validator(self):
        self.assertTrue(FloatTypeValidator("123.45").validate())
        self.assertTrue(FloatTypeValidator("123").validate())
        self.assertTrue(FloatTypeValidator(".45").validate())
        self.assertTrue(FloatTypeValidator("-123.45").validate())
        self.assertFalse(FloatTypeValidator("abc").validate())

    def test_boolean_validator(self):
        for val in ["true", "false", "1", "0", "TRUE", "FALSE"]:
            self.assertTrue(BooleanTypeValidator(val).validate())
        self.assertFalse(BooleanTypeValidator("yes").validate())
        self.assertFalse(BooleanTypeValidator("no").validate())

    def test_datetime_validator(self):
        self.assertTrue(DatetimeTypeValidator("2023-10-27T10:00:00Z").validate())
        self.assertTrue(DatetimeTypeValidator("2023-10-27T10:00:00+00:00").validate())
        self.assertFalse(DatetimeTypeValidator("2023-13-27").validate())
        self.assertFalse(DatetimeTypeValidator("abc").validate())

    def test_uuid_validator(self):
        self.assertTrue(UUIDTypeValidator("550e8400-e29b-41d4-a716-446655440000").validate())
        self.assertFalse(UUIDTypeValidator("not-a-uuid").validate())

    def test_builder_raises_error_on_unknown_variant(self):
        with self.assertRaises(TypeError):
            TypeValidatorBuilder.build_validator("unknown", "value")
            
    def test_builder_returns_correct_validator(self):
        validator = TypeValidatorBuilder.build_validator(TypeVariant.INTEGER, "123")
        self.assertIsInstance(validator, IntTypeValidator)
