from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator


PAGE_SIZE = 10


def paginate(objects_list, request, per_page=PAGE_SIZE):
    paginator = Paginator(objects_list, per_page)
    page_number = request.GET.get("page", 1)

    try:
        page = paginator.page(page_number)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(1)

    page.navigation = paginator.get_elided_page_range(page.number)
    return page
