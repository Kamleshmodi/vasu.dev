from aapcategory.models import Category

def memu_links(request):
    men_links = Category.objects.filter(gender='men')
    women_links = Category.objects.filter(gender='women')
    return {'men_links': men_links, 'women_links': women_links}


def get_context():
    return {"test": "value"}
