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
    def __init__(self, inventory_agent, catalog_agent):
        self.inventory = inventory_agent
        self.catalog = catalog_agent
        self.orders = {}
        self.next_id = 1

    def create_order(self, sku, quantity, customer):
        product = self.catalog.get_product(sku)
        if isinstance(product, str):
            return product  # error message
        if not self.inventory.check_stock(sku, quantity):
            return f"Insufficient stock for {sku}."
        order_id = self.next_id
        self.next_id += 1
        self.orders[order_id] = {
            "sku": sku,
            "quantity": quantity,
            "customer": customer,
            "status": "Processing",
        }
        self.inventory.reserve_stock(sku, quantity)
        return f"Order {order_id} created for {sku} (x{quantity})."

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

    def check_stock(self, sku, required):
        return self.stock.get(sku, 0) >= required

    def reserve_stock(self, sku, quantity):
        if self.check_stock(sku, quantity):
            self.stock[sku] -= quantity
            if self.stock[sku] <= self.reorder_threshold:
                return f"Stock low for {sku}. Trigger reorder."
            return f"Reserved {quantity} of {sku}."
        return f"Insufficient stock for {sku}."

    def replenish(self, sku, quantity):
        self.stock[sku] = self.stock.get(sku, 0) + quantity
        return f"Replenished {sku} by {quantity}. New stock: {self.stock[sku]}"

def run_mission(mission: str) -> str:
    # Simple dispatcher based on keywords
    # Initialize agents (stateless for this demo)
    catalog = CatalogAgent()
    inventory = InventoryAgent()
    order = OrderAgent(inventory, catalog)
    parts = mission.split("|")
    command = parts[0].strip().lower()
    try:
        if command == "add_product":
            _, sku, name, price, description = parts
            return catalog.add_product(sku.strip(), name.strip(), float(price), description.strip())
        if command == "set_stock":
            _, sku, qty = parts
            return inventory.set_stock(sku.strip(), int(qty))
        if command == "create_order":
            _, sku, qty, customer = parts
            return order.create_order(sku.strip(), int(qty), customer.strip())
        if command == "update_price":
            _, sku, new_price = parts
            return catalog.update_price(sku.strip(), float(new_price))
        if command == "replenish":
            _, sku, qty = parts
            return inventory.replenish(sku.strip(), int(qty))
        return f"Unknown command: {command}"
    except Exception as e:
        return f"Error processing mission: {e}"
