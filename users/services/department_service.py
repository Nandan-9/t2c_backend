from users.models import Department, Minister


def get_all_departments():
    return Department.objects.select_related("minister").order_by("name")


def get_department_by_id(department_id: int):
    try:
        return Department.objects.select_related("minister").get(pk=department_id)
    except Department.DoesNotExist:
        return None


def create_department(data: dict) -> Department:
    minister = None
    minister_id = data.get("minister_id")
    if minister_id is not None:
        try:
            minister = Minister.objects.get(pk=minister_id)
        except Minister.DoesNotExist:
            raise ValueError(f"Minister with id {minister_id} does not exist.")

    department = Department(name=data["name"], minister=minister)
    department.full_clean()
    department.save()
    return department


def update_department(department: Department, data: dict) -> Department:
    update_fields = []

    if "name" in data:
        department.name = data["name"]
        update_fields.append("name")

    if "minister_id" in data:
        minister_id = data["minister_id"]
        if minister_id is None:
            department.minister = None
        else:
            try:
                department.minister = Minister.objects.get(pk=minister_id)
            except Minister.DoesNotExist:
                raise ValueError(f"Minister with id {minister_id} does not exist.")
        update_fields.append("minister")

    if update_fields:
        department.full_clean()
        department.save(update_fields=update_fields)

    return department


def delete_department(department: Department) -> None:
    department.delete()
