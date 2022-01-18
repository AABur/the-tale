
import smart_imports

smart_imports.all()


def login_required(func):

    @functools.wraps(func)
    def wrapper(resource, *argv, **kwargs):
        from the_tale.accounts import logic as accounts_logic

        if resource.account.is_authenticated:
            return func(resource, *argv, **kwargs)
        response_type = views.mime_type_to_response_type(resource.request.META.get('HTTP_ACCEPT'))

        if resource.request.is_ajax() or response_type == 'json':
            return resource.auto_error('common.login_required', 'У Вас нет прав для проведения данной операции')

        return resource.redirect(accounts_logic.login_page_url(resource.request.get_full_path()))

    return wrapper


def staff_required(permissions=()):

    @functools.wraps(staff_required)
    def decorator(func):
        @functools.wraps(func)
        def wrapper(resource, *argv, **kwargs):
            if permissions:
                raise NotImplementedError('staff required decorator has not implemented for working with permissions list')
            if resource.account.is_authenticated and resource.account.is_staff:
                return func(resource, *argv, **kwargs)
            else:
                return resource.auto_error('common.staff_required', 'У Вас нет прав для проведения данной операции')

        return login_required(wrapper)

    return decorator


def superuser_required(permissions=()):

    @functools.wraps(staff_required)
    def decorator(func):
        @functools.wraps(func)
        def wrapper(resource, *argv, **kwargs):
            if permissions:
                raise NotImplementedError('superuser required decorator has not implemented for working with permissions list')
            if resource.account.is_authenticated and resource.account.is_superuser:
                return func(resource, *argv, **kwargs)
            else:
                return resource.auto_error('common.superuser_required', 'У Вас нет прав для проведения данной операции')

        return login_required(wrapper)

    return decorator


def lazy_property(func):

    lazy_name = '_%s__lazy' % func.__name__

    @functools.wraps(func)
    def wrapper(self):
        if not hasattr(self, lazy_name):
            setattr(self, lazy_name, func(self))
        return getattr(self, lazy_name)

    def deleter(self):
        if hasattr(self, lazy_name):
            delattr(self, lazy_name)

    return property(fget=wrapper, fdel=deleter)


def generator_to_list(generator):

    @functools.wraps(generator)
    def wrapper(*argv, **kwargs):
        return list(generator(*argv, **kwargs))

    return wrapper


def retry_on_exception(max_retries=None, exceptions=[Exception]):

    @functools.wraps(retry_on_exception)
    def decorator(func):

        @functools.wraps(func)
        def wrapper(*argv, **kwargs):
            retries_number = 0
            while True:
                retries_number += 1
                try:
                    return func(*argv, **kwargs)
                except Exception as e:

                    if retries_number == max_retries:
                        raise


                    found = any(isinstance(e, exception) for exception in exceptions)
                    if not found:
                        raise

        return wrapper

    return decorator


def debug_required(func):

    @functools.wraps(func)
    def wrapper(resource, *argv, **kwargs):
        if django_settings.DEBUG:
            return func(resource, *argv, **kwargs)
        raise django_http.Http404()

    return wrapper
