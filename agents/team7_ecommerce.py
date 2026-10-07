class CatalogAgent:
    def __init__(self):
        self.products = {}

    def add_product(self, sku, name, price, description=""):
        self.products[sku] = {
            "name": name,
            "price": price,
            "description": description,
        }
        return f"Product {sku} added."

    def update_price(self, sku, new_price):
        if sku in self.products:
            self.products[sku]["price"] = new_price
            return f"Price for {sku} updated to {new_price}."
        return f"SKU {sku} not found."

    def get_product(self, sku):
        return self.products.get(sku, f"SKU {sku} not found.")

class OrderAgent:
    def __init__(self):
        self.orders = {}
        self.next_id = 1

    def create_order(self, customer_id, items):
        order_id = self.next_id
        self.next_id += 1
        self.orders[order_id] = {
            "customer_id": customer_id,
            "items": items,
            "status": "created",
        }
        return f"Order {order_id} created."

    def update_status(self, order_id, status):
        if order_id in self.orders:
            self.orders[order_id]["status"] = status
            return f"Order {order_id} status updated to {status}."
        return f"Order {order_id} not found."

    def get_order(self, order_id):
        return self.orders.get(order_id, f"Order {order_id} not found.")

class InventoryAgent:
    def __init__(self):
        self.stock = {}
        self.reorder_threshold = 5

    def set_stock(self, sku, quantity):
        self.stock[sku] = quantity
        return f"Stock for {sku} set to {quantity}."

    def adjust_stock(self, sku, delta):
        if sku not in self.stock:
            self.stock[sku] = 0
        self.stock[sku] += delta
        return f"Stock for {sku} adjusted by {delta}, now {self.stock[sku]}."

    def check_reorder(self, sku):
        qty = self.stock.get(sku, 0)
        if qty <= self.reorder_threshold:
            return f"Reorder needed for {sku}: {qty} left."
        return f"Stock sufficient for {sku}: {qty} left."

def run_mission(mission: str) -> str:
    # Simple dispatcher based on keywords
    catalog = CatalogAgent()
    order = OrderAgent()
    inventory = InventoryAgent()
    parts = mission.split("|")
    action = parts[0].strip().lower()
    if action == "add_product":
        _, sku, name, price, description = parts
        return catalog.add_product(sku, name, float(price), description)
    if action == "update_price":
        _, sku, new_price = parts
        return catalog.update_price(sku, float(new_price))
    if action == "create_order":
        _, customer_id, items_str = parts
        # items_str format: sku1:qty1,sku2:qty2
        items = []
        for pair in items_str.split(","):
            sku, qty = pair.split(":")
            items.append({"sku": sku, "qty": int(qty)})
        return order.create_order(customer_id, items)
    if action == "update_order_status":
        _, order_id, status = parts
        return order.update_status(int(order_id), status)
    if action == "set_stock":
        _, sku, qty = parts
        return inventory.set_stock(sku, int(qty))
    if action == "adjust_stock":
        _, sku, delta = parts
        return inventory.adjust_stock(sku, int(delta))
    if action == "check_reorder":
        _, sku = parts
        return inventory.check_reorder(sku)
    return "Unknown mission command."
