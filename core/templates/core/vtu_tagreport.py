from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def render_vtu_report(context):
    html = f"""
    <div style='display:flex;gap:20px;margin-top:20px'>
        <div style='padding:20px;background:#fff;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.1);min-width:180px'>
            <h3>Total Sales</h3>
            <p>₦{report['total_sales']}</p>
        </div>
        <div style='padding:20px;background:#fff;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.1);min-width:180px'>
            <h3>Total Cost</h3>
            <p>₦{report['total_cost']}</p>
        </div>
        <div style='padding:20px;background:#fff;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.1);min-width:180px'>
            <h3>Profit</h3>
            <p><strong>₦{report['profit']}</strong></p>
        </div>
        <div style='padding:20px;background:#fff;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.1);min-width:180px'>
            <h3>Transactions</h3>
            <p>{report['count']}</p>
        </div>
    </div>
    """
    return html
