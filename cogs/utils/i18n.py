from fluent.runtime import FluentBundle, FluentResourceLoader

class Fluent(object):
    """
    Custom Fluent Localization

    Dirty AF :)
    """
    def __init__(
        self, locale, fallback, resource_ids, resource_loader,
        languages=None,
        use_isolating=False,
        bundle_class=None, functions=None,
    ):
        self.fallback = fallback
        self.resource_ids = resource_ids
        self.resource_loader = resource_loader
        self.use_isolating = use_isolating
        if bundle_class is None:
            from fluent.runtime import FluentBundle
            self.bundle_class = FluentBundle
        else:
            self.bundle_class = bundle_class
        self.functions = functions
        self.languages=languages or [fallback] + ([locale] if locale != fallback else [])
        self._set_locale(locale or "")

    def format_value(self, msg_id, args=None):
        for bundle in self._bundles():
            if not bundle.has_message(msg_id):
                continue
            msg = bundle.get_message(msg_id)
            if not msg.value:
                continue
            val, errors = bundle.format_pattern(msg.value, args)
            return val
        return msg_id

    def _set_locale(self, locale):
        if locale not in self.languages:
            print("Warning: {} not found!".format(locale))
        self.locale = locale
        self._bundle_cache = []
        self._bundle_it = self._iterate_bundles()

    def _create_bundle(self, locales):
        return self.bundle_class(
            locales, functions=self.functions, use_isolating=self.use_isolating
        )

    def _bundles(self):
        bundle_pointer = 0
        while True:
            if bundle_pointer == len(self._bundle_cache):
                try:
                    self._bundle_cache.append(next(self._bundle_it))
                except StopIteration:
                    return
            yield self._bundle_cache[bundle_pointer]
            bundle_pointer += 1

    def _iterate_bundles(self):
        locales = [self.locale, self.fallback]
        for first_loc in range(0, len(locales)):
            locs = locales[first_loc:]
            for resources in self.resource_loader.resources(locs[0], self.resource_ids):
                bundle = self._create_bundle(locs)
                for resource in resources:
                    bundle.add_resource(resource)
                yield bundle
    
    @property
    def language(self):
        return self.locale