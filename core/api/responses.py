from rest_framework.response import Response
from rest_framework import status


def success_response(data, status_code=status.HTTP_200_OK):
    return Response(
        {"success": True, "data": data},
        status=status_code,
    )


def error_response(errors, status_code=status.HTTP_400_BAD_REQUEST):
    return Response(
        {"success": False, "errors": errors},
        status=status_code,
    )


def paginated_response(page, data):
    return Response(
        {
            "success": True,
            "data": {
                "results": data,
                "pagination": {
                    "count": page.paginator.count,
                    "page": page.number,
                    "page_size": len(page.object_list),
                    "next": page.has_next() and page.next_page_number() or None,
                    "previous": page.has_previous() and page.previous_page_number() or None,
                },
            },
        }
    )
