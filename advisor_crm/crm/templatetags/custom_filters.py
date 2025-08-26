from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiply the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0
    
@register.filter
def format_name(user):
    """
    Format the user's name with first character of first and last name in uppercase.
    Returns formatted name or username if no name is available.
    """
    if hasattr(user, 'get_full_name'):
        full_name = user.get_full_name()
        if full_name.strip():
            # Split into parts and capitalize each part
            parts = full_name.split()
            formatted_parts = []
            for part in parts:
                if part:
                    formatted_parts.append(part[0].upper() + part[1:].lower())
            return ' '.join(formatted_parts)
    
    # Fallback to username if no name is available
    return user.username


@register.filter
def capitalize_name(name):
    """
    Capitalize the first character of each word in a name.
    """
    if name:
        parts = name.split()
        formatted_parts = []
        for part in parts:
            if part:
                formatted_parts.append(part[0].upper() + part[1:].lower())
        return ' '.join(formatted_parts)
    return name