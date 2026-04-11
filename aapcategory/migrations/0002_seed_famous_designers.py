from django.db import migrations


WOMEN_DESIGNERS = [
    'Alexander McQueen',
    'Carolina Herrera',
    'Donatella Versace',
    'Gabriela Hearst',
    'Isabel Marant',
    'Maria Grazia Chiuri',
    'Miuccia Prada',
    'Phoebe Philo',
    'Sarah Burton',
    'Simone Rocha',
    'Stella McCartney',
    'Tory Burch',
    'Victoria Beckham',
    'Vivienne Westwood',
]

MEN_DESIGNERS = [
    'Brunello Cucinelli',
    'Dries Van Noten',
    'Giorgio Armani',
    'Haider Ackermann',
    'Hedi Slimane',
    'Heron Preston',
    'Jonathan Anderson',
    'Kim Jones',
    'Nigo',
    'Ralph Lauren',
    'Rick Owens',
    'TOM FORD',
    'Thom Browne',
    'Virgil Abloh',
    'Yohji Yamamoto',
]


def add_famous_designers(apps, schema_editor):
    Designer = apps.get_model('aapcategory', 'Designer')

    for name in WOMEN_DESIGNERS:
        Designer.objects.get_or_create(name=name, gender='women')

    for name in MEN_DESIGNERS:
        Designer.objects.get_or_create(name=name, gender='men')


def remove_famous_designers(apps, schema_editor):
    Designer = apps.get_model('aapcategory', 'Designer')
    Designer.objects.filter(name__in=WOMEN_DESIGNERS, gender='women').delete()
    Designer.objects.filter(name__in=MEN_DESIGNERS, gender='men').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('aapcategory', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(add_famous_designers, remove_famous_designers),
    ]
