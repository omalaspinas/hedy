import json

import hedy
from website.auth import requires_login, is_teacher, current_user
import utils
import uuid
from flask import g, request, jsonify, redirect
from flask_helpers import render_template
import os
import hedyweb
import hedy_content
TRANSLATIONS = hedyweb.Translations ()
from config import config
cookie_name     = config ['session'] ['cookie_name']


def routes (app, database, achievements):
    global DATABASE
    global ACHIEVEMENTS
    DATABASE = database
    ACHIEVEMENTS = achievements

    @app.route('/classes', methods=['GET'])
    @requires_login
    def get_classes (user):
        if not is_teacher(user):
            return utils.error_page_403(error=403, ui_message='retrieve_class')
        return jsonify (DATABASE.get_teacher_classes (user ['username'], True))

    @app.route('/for-teachers/class/<class_id>', methods=['GET'])
    @requires_login
    def get_class (user, class_id):
        app.logger.info('This is info output')
        if not is_teacher(user):
            return utils.error_page_403(error=403, ui_message='retrieve_class')
        Class = DATABASE.get_class (class_id)
        if not Class or Class ['teacher'] != user ['username']:
            return utils.error_page(error=404,  ui_message='no_such_class')
        students = []
        for student_username in Class.get ('students', []):
            student = DATABASE.user_by_username (student_username)
            programs = DATABASE.programs_for_user(student_username)
            highest_level = max(program['level'] for program in programs) if len(programs) else 0
            sorted_public_programs = list(sorted([program for program in programs if program.get ('public')], key=lambda p: p['date']))
            if sorted_public_programs:
                latest_shared = sorted_public_programs[-1]
                latest_shared['link'] = f"/hedy/{latest_shared['id']}/view"
            else:
                latest_shared = None
            students.append ({'username': student_username, 'last_login': utils.datetotimeordate (utils.mstoisostring (student ['last_login'])), 'programs': len (programs), 'highest_level': highest_level, 'latest_shared': latest_shared})

        if utils.is_testing_request (request):
            return jsonify ({'students': students, 'link': Class ['link'], 'name': Class ['name'], 'id': Class ['id']})

        achievement = None
        if len(students) > 20:
            achievement = ACHIEVEMENTS.add_single_achievement(user['username'], "full_house")
        if achievement:
            achievement = json.dumps(achievement)

        teachers = os.getenv('BETA_TEACHERS', '').split(',')
        is_beta_teacher = user['username'] in teachers

        invites = []
        for invite in DATABASE.get_class_invites(Class['id']):
            invites.append({'username': invite['username'], 'timestamp': utils.datetotimeordate (utils.mstoisostring (invite['timestamp']))})

        return render_template ('class-overview.html', current_page='my-profile',
                                page_title=hedyweb.get_page_title('class overview'),
                                achievement=achievement, invites=invites,
                                is_beta_teacher=is_beta_teacher,
                                class_info={'students': students, 'link': os.getenv('BASE_URL') + '/hedy/l/' + Class ['link'],
                                            'name': Class ['name'], 'id': Class ['id']})

    @app.route('/class', methods=['POST'])
    @requires_login
    def create_class (user):
        if not is_teacher(user):
            return 'Only teachers can create classes', 403

        body = request.json
        # Validations
        if not isinstance(body, dict):
            return 'body must be an object', 400
        if not isinstance(body.get('name'), str):
            return 'name must be a string', 400

        # We use this extra call to verify if the class name doesn't already exist, if so it's a duplicate
        Classes = DATABASE.get_teacher_classes(user['username'], True)
        for Class in Classes:
            if Class['name'] == body['name']:
                return "duplicate", 200

        Class = {
            'id': uuid.uuid4().hex,
            'date': utils.timems (),
            'teacher': user ['username'],
            'link': utils.random_id_generator (7),
            'name': body ['name']
        }

        DATABASE.store_class (Class)
        achievement = ACHIEVEMENTS.add_single_achievement(user['username'], "ready_set_education")
        if achievement:
            return {'id': Class['id'], 'achievement': achievement}, 200
        return {'id': Class['id']}, 200

    @app.route('/class/<class_id>', methods=['PUT'])
    @requires_login
    def update_class (user, class_id):
        if not is_teacher(user):
            return 'Only teachers can update classes', 403

        body = request.json
        # Validations
        if not isinstance(body, dict):
            return 'body must be an object', 400
        if not isinstance(body.get('name'), str):
            return 'name must be a string', 400

        Class = DATABASE.get_class (class_id)
        if not Class or Class ['teacher'] != user ['username']:
            return 'No such class', 404

        # We use this extra call to verify if the class name doesn't already exist, if so it's a duplicate
        Classes = DATABASE.get_teacher_classes(user ['username'], True)
        for Class in Classes:
            if Class['name'] == body['name']:
                return "duplicate", 200

        Class = DATABASE.update_class (class_id, body ['name'])
        achievement = ACHIEVEMENTS.add_single_achievement(user['username'], "on_second_thoughts")
        if achievement:
            return {'achievement': achievement}, 200
        return {}, 200

    @app.route('/class/<class_id>', methods=['DELETE'])
    @requires_login
    def delete_class (user, class_id):
        Class = DATABASE.get_class (class_id)
        if not Class or Class ['teacher'] != user ['username']:
            return 'No such class', 404

        DATABASE.delete_class (Class)
        achievement = ACHIEVEMENTS.add_single_achievement(user['username'], "end_of_semester")
        if achievement:
            return {'achievement': achievement}, 200
        return {}, 200

    @app.route('/class/<class_id>/prejoin/<link>', methods=['GET'])
    def prejoin_class (class_id, link):
        Class = DATABASE.get_class (class_id)
        if not Class or Class ['link'] != link:
            return utils.error_page(error=404,  ui_message='invalid_class_link')
        user = {}
        if request.cookies.get (cookie_name):
            token = DATABASE.get_token(request.cookies.get (cookie_name))
            if token:
                if token ['username'] in Class.get ('students', []):
                    return render_template ('class-prejoin.html', joined=True,
                                            page_title=hedyweb.get_page_title('join class'),
                                            current_page='my-profile', class_info={'name': Class ['name']})
                user = DATABASE.user_by_username(token ['username'])

        return render_template ('class-prejoin.html', joined=False,
                                page_title=hedyweb.get_page_title('join class'),
                                current_page='my-profile',
                                class_info={
                                    'id': Class ['id'],
                                    'name': Class ['name'],
                                })

    @app.route('/class/join', methods=['POST'])
    @requires_login
    def join_class(user):
        body = request.json
        if 'id' in body:
            Class = DATABASE.get_class(body['id'])
        if not Class or Class ['id'] != body['id']:
            return utils.error_page(error=404,  ui_message='invalid_class_link')

        DATABASE.add_student_to_class(Class['id'], user['username'])
        DATABASE.remove_class_invite(user['username'])
        achievement = ACHIEVEMENTS.add_single_achievement(user['username'], "epic_education")
        if achievement:
            return {'achievement': achievement}, 200
        return {}, 200

    @app.route('/class/<class_id>/student/<student_id>', methods=['DELETE'])
    @requires_login
    def leave_class (user, class_id, student_id):
        Class = DATABASE.get_class (class_id)
        if not Class or (Class['teacher'] != user['username'] and student_id != user['username']):
            return g.auth_texts.get('ajax_error'), 400

        DATABASE.remove_student_from_class (Class['id'], student_id)
        achievement = None
        if Class['teacher'] == user['username']:
            achievement = ACHIEVEMENTS.add_single_achievement(user['username'], "detention")
        if achievement:
            return {'achievement': achievement}, 200
        return {}, 200

    @app.route('/for-teachers/customize-class/<class_id>', methods=['GET'])
    @requires_login
    def get_class_info(user, class_id):
        if not is_teacher(user):
            return utils.error_page(error=403, ui_message='retrieve_class')
        Class = DATABASE.get_class(class_id)
        if not Class or Class['teacher'] != user['username']:
            return utils.error_page(error=404,  ui_message='no_such_class')

        if hedy_content.Adventures(g.lang).has_adventures():
            adventures = hedy_content.Adventures(g.lang).get_adventure_keyname_name_levels()
        else:
            adventures = hedy_content.Adventures("en").get_adventure_keyname_name_levels()

        teacher_adventures = DATABASE.get_teacher_adventures(user['username']);
        customizations = DATABASE.get_class_customizations(class_id)
        customize_class_translations = hedyweb.PageTranslations('customize-class').get_page_translations(g.lang)

        return render_template('customize-class.html', page_title=hedyweb.get_page_title('customize class'),
                               class_info={'name': Class['name'], 'id': Class['id']}, max_level=hedy.HEDY_MAX_LEVEL,
                               adventures=adventures, page_translations=customize_class_translations,
                               teacher_adventures=teacher_adventures, customizations=customizations, current_page='my-profile')

    @app.route('/for-teachers/customize-class/<class_id>', methods=['DELETE'])
    @requires_login
    def delete_customizations(user, class_id):
        if not is_teacher(user):
            return utils.error_page(error=403, ui_message='retrieve_class')
        Class = DATABASE.get_class(class_id)
        if not Class or Class['teacher'] != user['username']:
            return utils.error_page(error=404, ui_message='no_such_class')

        DATABASE.delete_class_customizations(class_id)
        return {'success': g.auth_texts.get('customization_deleted')}, 200

    @app.route('/for-teachers/customize-class/<class_id>', methods=['POST'])
    @requires_login
    def update_customizations(user, class_id):
        if not is_teacher(user):
            return utils.error_page(error=403, ui_message='retrieve_class')
        Class = DATABASE.get_class(class_id)
        if not Class or Class['teacher'] != user['username']:
            return utils.error_page(error=404, ui_message='no_such_class')

        body = request.json
        #Validations
        if not isinstance(body, dict):
            return g.auth_texts.get('ajax_error'), 400
        if not isinstance(body.get('levels'), list):
            return "Levels must be a list", 400
        if not isinstance(body.get('adventures'), dict):
            return 'adventures must be a dict', 400

        #Values are always strings from the front-end -> convert to numbers
        levels = [int(i) for i in body['levels']]
        adventures = {}
        for name, adventure_levels in body['adventures'].items():
            adventures[name] = [int(i) for i in adventure_levels]

        customizations = {
            'id': class_id,
            'levels': levels,
            'adventures': adventures,
            'teacher_adventures': body['teacher_adventures']
        }

        DATABASE.update_class_customizations(customizations)
        return {'success': g.auth_texts.get('class_customize_success')}, 200

    @app.route('/invite_student', methods=['POST'])
    @requires_login
    def invite_student(user):
        body = request.json
        # Validations
        if not isinstance(body, dict):
            return g.auth_texts.get('ajax_error'), 400
        if not isinstance(body.get('username'), str):
            return g.auth_texts.get('username_invalid'), 400
        if not isinstance(body.get('class_id'), str):
            return 'class id must be a string', 400

        username = body.get('username').lower()
        class_id = body.get('class_id')

        if not is_teacher(user):
            return utils.error_page(error=403, ui_message='retrieve_class')
        Class = DATABASE.get_class(class_id)
        if not Class or Class['teacher'] != user['username']:
            return utils.error_page(error=404, ui_message='no_such_class')

        user = DATABASE.user_by_username(username)
        if not user:
            return g.auth_texts.get('student_not_existing'), 400
        if 'students' in Class and user['username'] in Class['students']:
            return g.auth_texts.get('student_already_in_class'), 400
        if DATABASE.get_username_invite(user['username']):
            return g.auth_texts.get('student_already_invite'), 400

        # So: The class and student exist and are currently not a combination -> invite!
        DATABASE.add_class_invite(username, class_id)
        return {}, 200

    @app.route('/remove_student_invite', methods=['POST'])
    @requires_login
    def remove_invite(user):
        body = request.json
        # Validations
        if not isinstance(body, dict):
            return g.auth_texts.get('ajax_error'), 400
        if not isinstance(body.get('username'), str):
            return g.auth_texts.get('username_invalid'), 400
        if not isinstance(body.get('class_id'), str):
            return 'class id must be a string', 400

        username = body.get('username')
        class_id = body.get('class_id')

        if not is_teacher(user) and username != user.get('username'):
            return utils.error_page(error=403, ui_message='retrieve_class')
        Class = DATABASE.get_class(class_id)
        if not Class or (Class['teacher'] != user['username'] and username != user.get('username')):
            return utils.error_page(error=404, ui_message='no_such_class')

        DATABASE.remove_class_invite(username)
        return {}, 200

    @app.route('/for-teachers/customize-adventure/view/<adventure_id>', methods=['GET'])
    @requires_login
    def view_adventure(user, adventure_id):
        if not is_teacher(user):
            return utils.error_page(error=403, ui_message='retrieve_adventure')
        adventure = DATABASE.get_adventure(adventure_id)
        if not adventure or adventure['creator'] != user['username']:
            return utils.error_page(error=404, ui_message='no_such_adventure')

        adventure['content'] = adventure['content'].replace("<pre>", "<pre id='" + str(adventure['level']) + "'>")
        return render_template('view-adventure.html', adventure=adventure,
                               page_title=hedyweb.get_page_title('view adventure'), current_page='my-profile')

    @app.route('/for-teachers/customize-adventure/<adventure_id>', methods=['GET'])
    @requires_login
    def get_adventure_info(user, adventure_id):
        if not is_teacher(user):
            return utils.error_page(error=403, ui_message='retrieve_adventure')
        adventure = DATABASE.get_adventure(adventure_id)
        if not adventure or adventure['creator'] != user['username']:
            return utils.error_page(error=404,  ui_message='no_such_adventure')

        return render_template('customize-adventure.html', page_title=hedyweb.get_page_title('customize adventure'),
                               adventure=adventure, max_level=hedy.HEDY_MAX_LEVEL, current_page='my-profile')

    @app.route('/for-teachers/customize-adventure', methods=['POST'])
    @requires_login
    def update_adventure(user):
        body = request.json
        # Validations
        if not isinstance(body, dict):
            return g.auth_texts.get('ajax_error'), 400
        if not isinstance(body.get('id'), str):
            return g.auth_texts.get('adventure_id_invalid'), 400
        if not isinstance(body.get('name'), str):
            return g.auth_texts.get('adventure_name_invalid'), 400
        if not isinstance(body.get('level'), str):
            return g.auth_texts.get('level_invalid'), 400
        if not isinstance(body.get('content'), str):
            return g.auth_texts.get('content_invalid'), 400
        if len(body.get('content')) < 20:
            return g.auth_texts.get('adventure_length'), 400
        if not isinstance(body.get('public'), bool):
            return g.auth_texts.get('adventure_length'), 400

        if not is_teacher(user):
            return utils.error_page(error=403, ui_message='retrieve_adventure')
        current_adventure = DATABASE.get_adventure(body['id'])
        if not current_adventure or current_adventure['creator'] != user['username']:
            return utils.error_page(error=404,  ui_message='no_such_adventure')

        adventures = DATABASE.get_teacher_adventures(user['username'])
        for adventure in adventures:
            if adventure['name'] == body['name'] and adventure['id'] != body['id']:
                return g.auth_texts.get('adventure_duplicate'), 400

        adventure = {
            'date': utils.timems(),
            'creator': user['username'],
            'name': body['name'],
            'level': body['level'],
            'content': body['content'],
            'public': body['public']
        }

        DATABASE.update_adventure(body['id'], adventure)
        return {'success': g.auth_texts.get('adventure_updated')}, 200

    @app.route('/for-teachers/customize-adventure/<adventure_id>', methods=['DELETE'])
    @requires_login
    def delete_adventure(user, adventure_id):
        if not is_teacher(user):
            return utils.error_page(error=403, ui_message='retrieve_adventure')
        adventure = DATABASE.get_adventure(adventure_id)
        if not adventure or adventure['creator'] != user['username']:
            return utils.error_page(error=404, ui_message='no_such_adventure')

        DATABASE.delete_adventure(adventure_id)
        return {}, 200

    @app.route('/for-teachers/create_adventure', methods=['POST'])
    @requires_login
    def create_adventure(user):
        if not is_teacher(user):
            return utils.error_page(error=403, ui_message='create_adventure')
        body = request.json
        adventures = DATABASE.get_teacher_adventures(user['username'])
        for adventure in adventures:
            if adventure['name'] == body['name']:
                return g.auth_texts.get('adventure_duplicate'), 400

        adventure = {
            'id': uuid.uuid4().hex,
            'date': utils.timems(),
            'creator': user['username'],
            'name': body['name'],
            'level': 1,
            'content': ""
        }

        DATABASE.store_adventure(adventure)
        return {'id': adventure['id']}, 200

    @app.route('/hedy/l/<link_id>', methods=['GET'])
    def resolve_class_link (link_id):
        Class = DATABASE.resolve_class_link (link_id)
        if not Class:
            return utils.error_page(error=404,  ui_message='invalid_class_link')
        return redirect(request.url.replace('/hedy/l/' + link_id, '/class/' + Class ['id'] + '/prejoin/' + link_id), code=302)
