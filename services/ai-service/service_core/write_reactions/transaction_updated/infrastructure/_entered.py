def entered[TRepository](repository: TRepository | None) -> TRepository:
    if repository is None:
        raise RuntimeError("this unit of work has not been entered")

    return repository
