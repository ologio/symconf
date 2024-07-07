from pathlib import Path
from symconf import ConfigManager


config_dir = Path(
    __file__, '..', 'test-config-dir/'
).resolve()
cm = ConfigManager(config_dir)

def test_config_map():
    file_map = cm.app_config_map('test')
    
    # from user
    assert 'none-none.aaa'    in file_map
    assert 'none-light.aaa'  in file_map
    assert 'test-dark.bbb'  in file_map
    assert 'test-light.ccc' in file_map

    # from generated
    assert 'test-none.aaa' in file_map

def test_matching_configs_exact():
    '''
    Test matching exact palette and scheme. Given strict mode not set (allowing relaxation
    to "none"), the order of matching should be

    1. (none, none)      :: none-none.aaa
    2. (none, scheme)    :: none-light.aaa
    3. (palette, none)   :: test-none.aaa & test-none.ddd
    4. (palette, scheme) :: test-light.ccc

    Yielding "test-none.aaa", "test-light.ccc", "test-none.ddd" (unique only on path name).
    '''
    any_light = cm.get_matching_configs(
        'test', 
        palette='test',
        scheme='light',
    )

    assert len(any_light) == 3 
    assert any_light['aaa'].name == 'test-none.aaa'
    assert any_light['ccc'].name == 'test-light.ccc'
    assert any_light['ddd'].name == 'test-none.ddd'

def test_matching_configs_any_palette():
    '''
    Test matching exact palette and scheme. Given strict mode not set (allowing relaxation
    to "none"), the order of matching should be

    1. (palette, none)   :: test-none.aaa & test-none.ddd & none-none.aaa
    2. (none, none)      :: none-none.aaa
    3. (palette, scheme) :: test-dark.bbb
    4. (none, scheme)    :: (nothing)

    Yielding "none-none.aaa" (should always overwrite "test-none.aaa" due to "any"'s
    preference for non-specific matches, i.e., "none"s), "test-none.ddd", "test-dark.bbb"
    (unique only on path name).
    '''
    any_dark = cm.get_matching_configs(
        'test', 
        palette='any',
        scheme='dark',
    )

    assert len(any_dark) == 3 
    assert any_dark['aaa'].name == 'none-none.aaa'
    assert any_dark['bbb'].name == 'test-dark.bbb'
    assert any_dark['ddd'].name == 'test-none.ddd'

def test_matching_configs_any_scheme():
    '''
    Test matching exact palette and scheme. Given strict mode not set (allowing relaxation
    to "none"), the order of matching should be

    1. (none, scheme)    :: none-light.aaa & none-none.aaa
    2. (none, none)      :: none-none.aaa
    3. (palette, scheme) :: test-dark.bbb & test-light.ccc & test-none.aaa & test-none.ddd
    4. (palette, none)   :: test-none.aaa & test-none.ddd

    Yielding "test-none.aaa", "test-none.ddd", "test-light.ccc", "test-dark.bbb"
    '''
    test_any = cm.get_matching_configs(
        'test', 
        palette='test',
        scheme='any',
    )

    assert len(test_any) == 4
    assert test_any['aaa'].name == 'test-none.aaa'
    assert test_any['bbb'].name == 'test-dark.bbb'
    assert test_any['ccc'].name == 'test-light.ccc'
    assert test_any['ddd'].name == 'test-none.ddd'

def test_matching_scripts():
    '''
    Test matching exact palette and scheme. Given strict mode not set (allowing relaxation
    to "none"), the order of matching should be

    1. (none, none)      :: none-none.sh
    2. (none, scheme)    :: none-light.sh
    3. (palette, none)   :: test-none.sh
    4. (palette, scheme) :: (nothing)

    Yielding (ordered by dec specificity) "test-none.sh" as primary match, then relaxation
    match "none-none.sh".
    '''
    test_any = cm.get_matching_scripts(
        'test', 
        palette='test',
        scheme='any',
    )

    assert len(test_any) == 2
    assert list(map(lambda p:p.name, test_any)) == ['test-none.sh', 'none-none.sh']

    any_light = cm.get_matching_scripts(
        'test', 
        palette='any',
        scheme='light',
    )

    assert len(any_light) == 2
    assert list(map(lambda p:p.name, any_light)) == ['none-light.sh', 'none-none.sh']

    any_dark = cm.get_matching_scripts(
        'test', 
        palette='any',
        scheme='dark',
    )

    assert len(any_dark) == 2
    assert list(map(lambda p:p.name, any_dark)) == ['test-none.sh', 'none-none.sh']
