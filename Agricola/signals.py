from django.db.models.signals import post_save, pre_delete, post_delete, pre_save
from django.db.models import F
from django.dispatch import receiver
from django.forms import ValidationError
from .models import Animal, EventoAnimal, MovimentacaoEstoque, HistoricoMovimentacao, EstoqueFazenda


#Atualiza o Estoque após uma movimentação
@receiver(post_save, sender=MovimentacaoEstoque)
def atualizar_estoque(sender, instance, created, **kwargs):
    if created:
        # Se for uma movimentação de entrada, adiciona ao estoque
        if instance.estq_tipo == 'entrada':
            EstoqueFazenda.objects.update_or_create(
                estq_empr=instance.estq_empr,
                estq_fili=instance.estq_fili,
                estq_faze=instance.estq_faze,
                estq_prod=instance.estq_prod,
                defaults={'estq_quant': F('estq_quant') + instance.estq_quant}
                
            )
        # Se for uma movimentação de saída, remove do estoque
        elif instance.estq_tipo == 'saida':
            EstoqueFazenda.objects.filter(
                estq_empr=instance.estq_empr,
                estq_fili=instance.estq_fili,
                estq_faze=instance.estq_faze,
                estq_prod=instance.estq_prod
            ).update(estq_quant=F('estq_quant') - instance.estq_quant)


@receiver(pre_delete, sender=MovimentacaoEstoque)
def verificar_estoque(sender, instance, **kwargs):
    if instance.estq_tipo == 'saida':
        # Verifica se há estoque suficiente antes de permitir a exclusão
        estoque_atual = EstoqueFazenda.objects.filter(
            estq_empr=instance.estq_empr,
            estq_fili=instance.estq_fili,
            estq_faze=instance.estq_faze,
            estq_prod=instance.estq_prod
        ).values_list('estq_quant', flat=True).first()
        
        if estoque_atual is None or estoque_atual < instance.estq_quant:
            raise ValidationError("Quantidade em saída maior do que a disponível no estoque.")
        

@receiver(post_delete, sender=MovimentacaoEstoque)
def atualizar_estoque_apos_exclusao(sender, instance, **kwargs):
    if instance.estq_tipo == 'saida':
        # Se for uma movimentação de saída, adiciona ao estoque novamente
        EstoqueFazenda.objects.update_or_create(
            estq_empr=instance.estq_empr,
            estq_fili=instance.estq_fili,
            estq_faze=instance.estq_faze,
            estq_prod=instance.estq_prod,
            defaults={'estq_quant': F('estq_quant') + instance.estq_quant}
        )


@receiver(post_save, sender=MovimentacaoEstoque)
def registrar_historico_movimentacao(sender, instance, created, **kwargs):
    if created:
        HistoricoMovimentacao.objects.create(
            estq_empr=instance.estq_empr,
            estq_fili=instance.estq_fili,
            estq_faze=instance.estq_faze,
            estq_prod=instance.estq_prod,
            estq_quant=instance.estq_quant,
            estq_tipo=instance.estq_tipo,
            estq_data=instance.estq_data,
            estq_obse=instance.estq_obsw,
        )