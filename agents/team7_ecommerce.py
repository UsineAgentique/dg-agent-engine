# team7_ecommerce pole implementation

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
            return product
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
        return f"Order {order_id} created for {sku} x{quantity}."
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
    def check_stock(self, sku, quantity):
        return self.stock.get(sku, 0) >= quantity
    def reserve_stock(self, sku, quantity):
        if self.check_stock(sku, quantity):
            self.stock[sku] -= quantity
            if self.stock[sku] <= self.reorder_threshold:
                return f"Stock low for {sku}. Trigger reorder."
            return f"Reserved {quantity} of {sku}."
        return f"Not enough stock for {sku}."
    def get_stock(self, sku):
        return self.stock.get(sku, 0)

def run_mission(mission: str) -> str:
    # Simple dispatcher based on mission keyword
    parts = mission.split(":", 1)
    if len(parts) != 2:
        return "Invalid mission format. Use 'Agent:action'."
    agent_name, action = parts[0].strip().lower(), parts[1].strip()
    # Initialize shared agents
    inventory = InventoryAgent()
    catalog = CatalogAgent()
    order = OrderAgent(inventory, catalog)
    if agent_name == "catalog":
        # Expected actions: add, price, get
        if action.startswith("add "):
            _, sku, name, price = action.split()
            return catalog.add_product(sku, name, float(price))
        if action.startswith("price "):
            _, sku, new_price = action.split()
            return catalog.update_price(sku, float(new_price))
        if action.startswith("get "):
            _, sku = action.split()
            return str(catalog.get_product(sku))
    if agent_name == "order":
        if action.startswith("create "):
            _, sku, qty, customer = action.split()
            return order.create_order(sku, int(qty), customer)
        if action.startswith("status "):
            _, oid, status = action.split()
            return order.update_status(int(oid), status)
        if action.startswith("get "):
            _, oid = action.split()
            return str(order.get_order(int(oid)))
    if agent_name == "inventory":
        if action.startswith("set "):
            _, sku, qty = action.split()
            return inventory.set_stock(sku, int(qty))
        if action.startswith("get "):
            _, sku = action.split()
            return f"Stock for {sku}: {inventory.get_stock(sku)}"
    return "Unknown agent or action."
