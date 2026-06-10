package utilities

type Option[T any] struct {
	Value T
	IsSet bool
}

func BuildOption[T any](value T) Option[T] {
	return Option[T]{
		Value: value,
		IsSet: true,
	}
}

func EmptyOption[T any]() Option[T] {
	return Option[T]{
		IsSet: false,
	}
}

func (opt *Option[T]) DefaultOption(fallback T) {
	if opt.IsSet == false {
		opt.Value = fallback
	}
}
