from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Pedido',
            fields=[
                ('id', models.CharField(max_length=36, primary_key=True, serialize=False)),
                ('cliente', models.CharField(max_length=100)),
                ('total', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('status', models.CharField(default='pendente', max_length=20)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'pedidos',
                'ordering': ['-criado_em'],
            },
        ),
        migrations.CreateModel(
            name='ItemPedido',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('produto', models.CharField(max_length=100)),
                ('qty', models.IntegerField()),
                ('preco', models.DecimalField(decimal_places=2, max_digits=10)),
                ('pedido', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='itens',
                    to='pedidos.pedido',
                )),
            ],
            options={
                'db_table': 'itens_pedido',
            },
        ),
    ]
