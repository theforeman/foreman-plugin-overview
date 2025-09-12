from dataclasses import dataclass, field

import yaml

# OS-specific packages use this path
DEBIAN_RELEASE = 'bookworm'
PACKAGING_URL = 'https://github.com/theforeman/foreman-packaging'


@dataclass
class Entry:
    short_name: str
    name: str | None = None
    url: str | None = None
    github_org: str = 'theforeman'
    installer: bool = True
    description: str | None = None

    @property
    def ci_badges(self):
        return []

    def __post_init__(self):
        if not self.name:
            self.name = self.short_name
        if not self.url:
            self.url = f'https://github.com/{self.github_org}/{self.name}'


class PuppetModule(Entry): # pylint: disable=too-few-public-methods
    @property
    def ci_badges(self):
        url = f'{self.url}/actions/workflows/ci.yml'
        return [f"[![CI]({url}/badge.svg)]({url})"]

    def __post_init__(self):
        if not self.name:
            self.name = f'puppet-{self.short_name}'
        super().__post_init__()


@dataclass
class PackagedEntry(Entry):
    rpm: str | None = None
    rpm_directory: str = 'plugins'
    deb: str | None = None
    deb_directory: str = 'plugins'
    puppet_acceptance_tests: str | None = None
    translations: str | None | bool = None
    github_team: str | None = None
    satellite: bool | None = False
    tests: dict = field(default_factory=dict)

    def __post_init__(self):
        super().__post_init__()

        if self.rpm is True:
            self.rpm = f'rubygem-{self.name}'
        if self.deb is True:
            self.deb = f'ruby-{self.name.replace("_", "-")}'

        if self.translations is True:
            self.translations = f'https://app.transifex.com/foreman/foreman/{self.name}/'
        elif self.translations:
            self.translations = f'https://app.transifex.com/foreman/foreman/{self.translations}/'

    @property
    def github_team_url(self):
        if not self.github_team:
            return None
        org, name = self.github_team.split('/')
        return f'https://github.com/orgs/{org}/teams/{name}'

    @property
    def rpm_url(self):
        if not self.rpm:
            return None
        return f'{PACKAGING_URL}/tree/rpm/develop/packages/{self.rpm_directory}/{self.rpm}'

    @property
    def deb_url(self):
        if not self.deb:
            return None
        return f'{PACKAGING_URL}/tree/deb/develop/{self.deb_directory}/{self.deb}'

    @property
    def puppet_module(self):
        return None  # implemented by a subclass

    @property
    def puppet_acceptance_tests_url(self):
        if not self.puppet_acceptance_tests:
            return None
        return f'https://github.com/theforeman/{self.puppet_module}/tree/master/spec/acceptance/{self.puppet_acceptance_tests}_spec.rb'  # pylint: disable=line-too-long

    @property
    def github_test_urls(self):
        return [(f'GitHub {label}', f'{self.url}/actions/workflows/{test}') for (label, test) in self.tests.get('github', {}).items()]

    @property
    def jenkins_test_urls(self):
        if not self.tests.get('jenkins'):
           return []
        return [('Jenkins', f'https://ci.theforeman.org/job/{self.tests["jenkins"]}')]

    @property
    def puppet_test_urls(self):
        return [('Puppet', self.puppet_acceptance_tests_url)]

    @property
    def test_urls(self):
        return [(label, url) for (label, url) in (self.puppet_test_urls + self.github_test_urls + self.jenkins_test_urls) if url]


class ForemanPlugin(PackagedEntry):
    def __post_init__(self):
        if not self.name:
            self.name = f'foreman_{self.short_name}'
        super().__post_init__()

    @property
    def puppet_module(self):
        return 'puppet-foreman'


class SmartProxyPlugin(PackagedEntry): # pylint: disable=too-few-public-methods
    def __post_init__(self):
        if not self.name:
            self.name = f'smart_proxy_{self.short_name}'
        if self.deb is True:
            self.deb = self.name.replace("-", "_")
        if self.puppet_acceptance_tests is True:
            self.puppet_acceptance_tests = self.short_name
        super().__post_init__()

    @property
    def puppet_module(self):
        return 'puppet-foreman_proxy'

@dataclass
class HammerPlugin(PackagedEntry):
    deb_directory: str = f'dependencies/{DEBIAN_RELEASE}'

    def __post_init__(self):
        if not self.name:
            self.name = f'hammer_cli_{self.short_name}'
        if not self.url:
            # A lot of repos use dashes, unlike the gem name
            self.url = f'https://github.com/{self.github_org}/hammer-cli-{self.short_name.replace("_", "-")}'
        if self.deb is True:
            self.deb = self.name.replace("-", "_")
        if self.puppet_acceptance_tests is None:
            self.puppet_acceptance_tests = True
        super().__post_init__()

    @property
    def puppet_module(self):
        return 'puppet-foreman'

    @property
    def puppet_acceptance_tests_url(self):
        if not self.puppet_acceptance_tests:
            return None
        return f'https://github.com/theforeman/{self.puppet_module}/tree/master/spec/acceptance/foreman_cli_plugins_spec.rb'  # pylint: disable=line-too-long

@dataclass
class ClientThing(PackagedEntry):
    rpm_directory: str = 'client'
    installer: bool = False

    def __post_init__(self):
        if self.rpm is True:
            self.rpm = self.short_name
        if self.deb is True:
            self.deb = self.short_name
        super().__post_init__()


@dataclass
class Library(PackagedEntry):
    deb_directory: str = f'dependencies/{DEBIAN_RELEASE}'
    rpm_directory: str = 'foreman'
    installer: bool = False

    def __post_init__(self):
        if self.deb is True:
            self.deb = self.short_name
        super().__post_init__()


def load_config(config):
    data = yaml.safe_load(config)

    data['cli']['plugins'] = [HammerPlugin(short_name=plugin_id, **(plugin or {}))
      for plugin_id, plugin in data['cli']['plugins'].items()]

    data['foreman']['plugins'] = [ForemanPlugin(short_name=plugin_id, **(plugin or {}))
      for plugin_id, plugin in data['foreman']['plugins'].items()]

    data['smart_proxy']['modules'] = [SmartProxyPlugin(short_name=module_id, **(module or {}))
      for module_id, module in data['smart_proxy']['modules'].items()]

    data['smart_proxy']['providers'] = [SmartProxyPlugin(short_name=provider_id, **(provider or {}))
      for provider_id, provider in data['smart_proxy']['providers'].items()]

    data['installer']['modules'] = [PuppetModule(short_name=module_id, **(module or {}))
      for module_id, module in data['installer']['modules'].items()]

    data['client'] = [ClientThing(short_name=repository_id, **(repository or {}))
      for repository_id, repository in data['client'].items()]

    data['libraries'] = [Library(short_name=repository_id, **(repository or {}))
      for repository_id, repository in data['libraries'].items()]

    data['auxiliary'] = [Entry(short_name=repository_id, **(repository or {}))
      for repository_id, repository in data['auxiliary'].items()]

    return data
