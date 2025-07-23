from django import template

register = template.Library()

@register.inclusion_tag('base/task_tree.html')
def show_task_tree(task):
    subtasks = task.subtasks.all()
    return {'task': task, 'subtasks': subtasks}
