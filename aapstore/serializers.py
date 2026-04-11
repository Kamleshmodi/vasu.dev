# vasu/serializers.py
from rest_framework import serializers
from aapstore.models import Order, OrderItem

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['item_id', 'name', 'price', 'quantity']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = ['full_name', 'mobile', 'address', 'city', 'state', 'zip_code', 'total_price', 'payment_method', 'items']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        # यहाँ बदलाव किया गया है: context से user को प्राप्त करें
        user = self.context['request'].user
        
        # Order को user के साथ बनाएं
        order = Order.objects.create(user=user, **validated_data)
        
        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)
        return order
