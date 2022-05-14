from utils.format import inline_wordbyword_diff

from github import Github
from aiohttp import ClientSession
import asyncio
from unidiff import PatchSet
from io import StringIO

import vdf
from os import getenv
from dotenv import load_dotenv
load_dotenv(dotenv_path='../env.env', verbose=True)
GIT_PERSONAL_TOKEN = getenv('GIT_PERSONAL_TOKEN')


async def human_commit(repo, commits, test_num=0):
    diff = repo.compare(commits[test_num + 1].sha, commits[test_num].sha)
    repo_url = 'https://github.com/SteamDatabase/GameTracking-Dota2'

    async def get_diff_string():
        async with ClientSession() as ses:
            async with ses.get(diff.diff_url) as response:
                return await response.text()

    ignored_files = [
        'game/bin/built_from_cl.txt',  # just contains build version number like `7200634`
        'game/dota/steam.inf'  # contains steam client server version which we have in embed title anyway
    ]
    ignored_gennames = [
        'linux',  # let's ignore all files about linux
        'win64',  # same about Windows
    ]
    loc_langs = [  # 'english' and 'localization' are not there
        'brazilian', 'bulgarian', 'czech', 'danish', 'dutch', 'finnish', 'french', 'german', 'greek',
        'hungarian', 'italian', 'japanese', 'korean', 'koreana', 'latam', 'norwegian', 'polish', 'portuguese',
        'romanian', 'russian', 'schinese', 'spanish', 'swedish', 'tchinese', 'thai', 'turkish', 'ukrainian', 'vietnamese'
    ]
    crc_checks = [  # useful to check myself, also have mentions of non-public files
        'game/dota/pak01_dir.txt'
    ]

    patch_set = PatchSet(await get_diff_string())
    human = set()  # set containing strings that will be human-readable patch notes
    robot_string = ''  # not parsed changes will be trashed there

    def get_crc_checked_files():
        crcfiles = [x for x in commits[0 + test_num].files if x.filename in crc_checks]
        res_list = []
        for x in crcfiles:
            for ln in iter(x.patch.splitlines()):
                if ln.startswith('+'):
                    res_list.append(ln[1:].split(' ')[0])
        return res_list
    crc_files = get_crc_checked_files()

    def remove_from_crc(filefilename):
        for name in crc_files:
            if name in filefilename:
                crc_files.remove(name)
    for pfile in patch_set:
        if any([name in pfile.path for name in ignored_gennames + ignored_files + crc_checks]):
            remove_from_crc(pfile.path)
            continue
        elif any([lang in pfile.path for lang in loc_langs]):
            human.add('Localization Update')
            remove_from_crc(pfile.path)
            continue
        elif 'english' in pfile.path:
            add_dict = {}
            remove_dict = {}
            for hunk in pfile:
                for line in hunk:
                    try:
                        if line.is_added:
                            key = line.value.split('"')[1]
                            value = line.value.split('"')[3]
                            add_dict[key] = value
                        if line.is_removed:
                            key = line.value.split('"')[1]
                            value = line.value.split('"')[3]
                            remove_dict[key] = value
                    except IndexError:
                        pass

            for key in add_dict:
                if key in remove_dict:
                    human.add(f'Changed string `{key}`: "{inline_wordbyword_diff(remove_dict[key], add_dict[key])}"')
                else:
                    human.add(f'Created string `{key}`: "{add_dict[key]}"')
            for key in remove_dict:
                if key not in add_dict:
                    human.add(f'Removed string `{key}`: "{remove_dict[key]}"')
            remove_from_crc(pfile.path)
            continue
        elif pfile.path == 'game/dota/pak01_dir/scripts/items/items_game.txt':

            curr_url = f'{repo_url}/raw/{commits[0 + test_num].sha}/{pfile.path}'
            old_url = curr_url.replace(commits[0 + test_num].sha, commits[1 + test_num].sha)

            async with ClientSession() as session:
                async with session.get(curr_url) as resp:
                    curr_dict = vdf.loads(await resp.text())
                async with session.get(old_url) as resp:
                    old_dict = vdf.loads(await resp.text())

            names_array = []
            data_array = []

            def my_dict_diff(new_dict, old_dict, name_candidate=''):
                for key in new_dict:
                    if key in old_dict:
                        if new_dict[key] != old_dict[key]:
                            try:
                                name_candidate = new_dict[key]['name']
                            except:
                                pass
                            if isinstance(new_dict[key], dict):
                                my_dict_diff(new_dict[key], old_dict[key], name_candidate=name_candidate)
                            else:
                                names_array.append(name_candidate)
                                data_array.append([key, old_dict[key], new_dict[key]])
            my_dict_diff(curr_dict, old_dict)
            for name, data in zip(names_array, data_array):
                human.add('Item `{0} ` was modified: `{1}` from `{2}` to `{3}`'.format(name, *data))
            remove_from_crc(pfile.path)
            continue
        elif pfile.path == 'game/dota/pak01_dir/scripts/npc/npc_abilities.txt':
            curr_url = f'{repo_url}/raw/{commits[0 + test_num].sha}/{pfile.path}'
            old_url = curr_url.replace(commits[0 + test_num].sha, commits[1 + test_num].sha)
            async with ClientSession() as session:
                async with session.get(curr_url) as resp:
                    curr_dict1 = vdf.loads(await resp.text())
                async with session.get(old_url) as resp:
                    old_dict1 = vdf.loads(await resp.text())

            #print(curr_dict)
            rem_array = []
            add_array = []
            mod_array = []

            def myh_dict_diff(new_dict, old_dict, name_candidate='', depth=0):
                for key in new_dict:
                    if key in old_dict:
                        if new_dict[key] != old_dict[key]:
                            if depth == 1:
                                name_candidate = key
                            if isinstance(new_dict[key], dict):
                                depth += 1
                                myh_dict_diff(new_dict[key], old_dict[key], name_candidate=name_candidate, depth=depth)
                            else:
                                mod_array.append([name_candidate, key, old_dict[key], new_dict[key]])
                    else:
                        add_array.append([name_candidate, key, new_dict[key]])

            myh_dict_diff(curr_dict1, old_dict1)
            for data in mod_array:
                human.add('Ability `{0}` was modified: `{1}` from `{2}` to `{3}`'.format(*data))
            for data in add_array:  # we can use localisation files to get a real name of ability later
                human.add('Ability `{0}`: a new param `{1}` was added: `{2}`'.format(*data))
            remove_from_crc(pfile.path)
            continue
        else:
            robot_string += f'{pfile.path}\n'
            for hunk in pfile:
                for line in hunk:
                    if line.is_added or line.is_removed:
                        robot_string += f'{line.line_type}{line.value}'
        # print('=== we dont know how to parse: ' + file.filename + '===')  # TODO: REMOVE THIS !!!

    human_string = '• ' + '\n• '.join(human) if len(human) else ''
    robot_string = 'CRC\n'.join(crc_files) + '\n' + robot_string if len(robot_string) or len(crc_files) else ''
    return human_string, robot_string


async def gitmain():
    g = Github(GIT_PERSONAL_TOKEN)
    repo = g.get_repo("SteamDatabase/GameTracking-Dota2")
    commits = repo.get_commits()

    test_num = 0
    print(commits[test_num].html_url)
    human_str, robot_str = await human_commit(repo, commits, test_num=test_num)
    print('\n❤❤❤ Human readable patch notes ❤❤❤')
    print(human_str)
    print('\n❤❤❤ Remaining unparsed changes ❤❤❤')
    print(robot_str)


if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(gitmain())
    #loop.close()

