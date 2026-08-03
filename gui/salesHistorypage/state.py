def initialize_sales_history_state(page, parent):
    page.username = parent.username
    page.setObjectName("MainContent")
    page.filtered_sales = []
    page._all_sales = None
    page._show_all_sales_requested = False
    page._sales_load_thread = None
    page._sales_load_worker = None
    page._sale_options_dialog = None
    page._is_closing = False
