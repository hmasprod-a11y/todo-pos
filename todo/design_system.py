"""Shared ToDo POS visual tokens and ttk components.

Keep semantic colors and default widget metrics here. Screen-specific layouts may
use these tokens while retaining their own content and operational shortcuts.
"""
from tkinter import ttk

COLORS = {
    'canvas': '#F6F7FB',
    'nav': '#1E293B',
    'ink': '#0F172A',
    'soft': '#F1F5F9',
    'danger': '#DC2626',
    'success': '#15803D',
    'selection': '#DBEAFE',
    'selection_pressed': '#BFDBFE',
    'disabled': '#94A3B8',
    'border': '#E2E8F0',
    'border_active': '#CBD5E1',
    'danger_hover': '#B91C1C',
    'danger_pressed': '#991B1B',
    'success_hover': '#166534',
    'success_pressed': '#14532D',
    'primary': '#2563EB',
    'primary_hover': '#1D4ED8',
    'nav_hover': '#334155',
    'muted': '#475569',
    'field': '#F8FAFC',
    'white': '#FFFFFF',
}
FONT_FAMILY = 'Segoe UI'
SPACE = {'xs': 4, 'sm': 8, 'md': 12, 'lg': 16, 'xl': 24}
TARGET_MIN_TOUCH_HEIGHT = 44


def configure_ttk(root):
    """Apply the existing visual language consistently to all ttk widgets."""
    st = ttk.Style(root)
    try:
        st.theme_use("clam")
    except Exception:
        pass
    root.configure(background=COLORS['canvas'])
    root.option_add('*Font', ('Segoe UI', 10))
    st.configure('.', font=('Segoe UI',10),background=COLORS['canvas'],foreground=COLORS['nav'])
    st.configure('TFrame',background=COLORS['canvas'])
    st.configure('TLabel',background=COLORS['canvas'])
    st.configure('TButton',font=('Segoe UI',10,'bold'),padding=(12,10),background=COLORS['white'],borderwidth=0)
    st.configure('Soft.TButton',font=('Segoe UI',10,'bold'),padding=(12,10),background=COLORS['soft'],foreground=COLORS['ink'])
    st.configure('Danger.TButton',font=('Segoe UI',10,'bold'),padding=(12,10),background=COLORS['danger'],foreground=COLORS['white'])
    st.configure('Success.TButton',font=('Segoe UI',10,'bold'),padding=(12,10),background=COLORS['success'],foreground=COLORS['white'])
    st.map('TButton',background=[('active',COLORS['selection']),('pressed',COLORS['selection_pressed'])],foreground=[('disabled',COLORS['disabled'])])
    st.map('Soft.TButton',background=[('active',COLORS['border']),('pressed',COLORS['border_active'])])
    st.map('Danger.TButton',background=[('active',COLORS['danger_hover']),('pressed',COLORS['danger_pressed'])],foreground=[('active',COLORS['white']),('pressed',COLORS['white'])])
    st.map('Success.TButton',background=[('active',COLORS['success_hover']),('pressed',COLORS['success_pressed'])],foreground=[('active',COLORS['white']),('pressed',COLORS['white'])])
    st.configure('Primary.TButton',background=COLORS['primary'],foreground=COLORS['white'],font=('Segoe UI',12,'bold'))
    st.map('Primary.TButton',background=[('active',COLORS['primary_hover'])],foreground=[('active',COLORS['white'])])
    st.configure('Sidebar.TFrame',background=COLORS['nav'])
    st.configure('Sidebar.TLabel',background=COLORS['nav'],foreground=COLORS['white'])
    st.configure('Sidebar.TButton',background=COLORS['nav'],foreground=COLORS['border'],anchor='w',padding=(12,12))
    st.map('Sidebar.TButton',background=[('active',COLORS['nav_hover'])],foreground=[('active',COLORS['white'])])
    st.configure('Card.TFrame',background=COLORS['white'])
    st.configure('Card.TLabel',background=COLORS['white'])
    st.configure('CardTitle.TLabel',background=COLORS['white'],font=('Segoe UI',15,'bold'))
    # Shared visual language for forms, settings and operational screens.
    st.configure('TLabelframe',background=COLORS['white'],borderwidth=1,relief='solid')
    st.configure('TLabelframe.Label',background=COLORS['white'],foreground=COLORS['nav_hover'],font=('Segoe UI',10,'bold'))
    st.configure('TSeparator',background=COLORS['border'])
    st.configure('TCheckbutton',background=COLORS['white'],foreground=COLORS['nav_hover'],font=('Segoe UI',10))
    st.configure('TRadiobutton',background=COLORS['white'],foreground=COLORS['nav_hover'],font=('Segoe UI',10))
    st.configure('Search.TEntry',font=('Segoe UI',17),padding=(10,8),fieldbackground=COLORS['white'],foreground=COLORS['ink'])
    st.configure('Quantity.TEntry',font=('Segoe UI',17,'bold'),padding=(8,8),fieldbackground=COLORS['field'],foreground=COLORS['ink'])
    st.configure('TNotebook',background=COLORS['canvas'],borderwidth=0)
    st.configure('TNotebook.Tab',font=('Segoe UI',10,'bold'),padding=(16,9),background=COLORS['border'],foreground=COLORS['muted'])
    st.map('TNotebook.Tab',background=[('selected',COLORS['white']),('active',COLORS['selection'])],foreground=[('selected',COLORS['ink'])])
    st.configure('Title.TLabel',font=('Segoe UI',23,'bold'))
    st.configure('Accent.TLabel',foreground=COLORS['primary'],font=('Segoe UI',12,'bold'))
    st.configure('Total.TLabel',background=COLORS['white'],foreground=COLORS['primary'],font=('Segoe UI',28,'bold'))
    st.configure('Treeview',font=('Segoe UI',10),rowheight=36,background=COLORS['white'],fieldbackground=COLORS['white'],foreground=COLORS['ink'],borderwidth=0)
    st.configure('Treeview.Heading',font=('Segoe UI',10,'bold'),padding=(10,10),background=COLORS['border'],foreground=COLORS['nav_hover'],relief='flat')
    st.map('Treeview',background=[('selected',COLORS['selection'])],foreground=[('selected',COLORS['ink'])])
    st.map('Treeview.Heading',background=[('active',COLORS['border_active'])])
    st.configure('Catalog.Treeview',rowheight=56,font=('Segoe UI',10))
    st.configure('Cart.Treeview',rowheight=50,font=('Segoe UI',10,'bold'))


