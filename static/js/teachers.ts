import { modal, error } from './modal';
import { auth } from './auth';
import {getHighlighter, showAchievements, turnIntoAceEditor} from "./app";

import DOMPurify from 'dompurify'

export function create_class() {
  modal.prompt (auth.texts['class_name_prompt'], '', function (class_name) {
    if (!class_name) {
      modal.alert(auth.texts['class_name_empty'], 2000, true);
      return;
    }
    $.ajax({
      type: 'POST',
      url: '/class',
      data: JSON.stringify({
        name: class_name
      }),
      contentType: 'application/json',
      dataType: 'json'
    }).done(function(response) {
      if (response.achievement) {
        showAchievements(response.achievement, false, '/for-teachers/customize-class/' + response.id);
      } else {
        window.location.pathname = '/for-teachers/customize-class/' + response.id ;
      }
    }).fail(function(err) {
      if (err.responseText == "duplicate") {
        modal.alert(auth.texts['class_name_duplicate'], 2000, true);
        return;
      }
      console.error(err);
      error.show(ErrorMessages['Connection_error'], JSON.stringify(err));
    });
  });
}

export function rename_class(id: string) {
  modal.prompt (auth.texts['class_name_prompt'], '', function (class_name) {
    if (!class_name) {
      modal.alert(auth.texts['class_name_empty'], 2000, true);
      return;
    }
    $.ajax({
      type: 'PUT',
      url: '/class/' + id,
      data: JSON.stringify({
        name: class_name
      }),
      contentType: 'application/json',
      dataType: 'json'
    }).done(function(response) {
      if (response.achievement) {
        showAchievements(response.achievement, true, "");
      } else {
        location.reload();
      }
    }).fail(function(err) {
      if (err.responseText == "duplicate") {
        modal.alert(auth.texts['class_name_duplicate'], 2000, true);
        return;
      }
      console.error(err);
      error.show(ErrorMessages['Connection_error'], JSON.stringify(err));
    });
  });
}

export function delete_class(id: string) {
  modal.confirm (auth.texts['delete_class_prompt'], function () {

    $.ajax({
      type: 'DELETE',
      url: '/class/' + id,
      contentType: 'application/json',
      dataType: 'json'
    }).done(function(response) {
      if (response.achievement) {
        showAchievements(response.achievement, false, '/for-teachers');
      } else {
        window.location.pathname = '/for-teachers';
      }
    }).fail(function(err) {
      console.error(err);
      error.show(ErrorMessages['Connection_error'], JSON.stringify(err));
    });
  });
}

export function join_class(id: string, name: string) {
  // If there's no session but we want to join the class, we store the program data in localStorage and redirect to /login.
  if (! auth.profile) {
    return modal.confirm (auth.texts['join_prompt'], function () {
      localStorage.setItem ('hedy-join', JSON.stringify ({id: id, name: name}));
      window.location.pathname = '/login';
      return;
    });
  }

  $.ajax({
      type: 'POST',
      url: '/class/join',
      contentType: 'application/json',
      data: JSON.stringify({
        id: id,
        name: name
      }),
      dataType: 'json'
    }).done(function(response) {
      if (response.achievement) {
          showAchievements(response.achievement, false, '/programs');
      } else {
          window.location.pathname = '/programs';
      }
    }).fail(function(err) {
      console.error(err);
      error.show(ErrorMessages['Connection_error'], JSON.stringify(err));
    });
}

export function invite_student(class_id: string) {
    modal.prompt (auth.texts['invite_prompt'], '', function (username) {
      if (!username) {
          return modal.alert(auth.texts['username_empty']);
      }
      $.ajax({
          type: 'POST',
          url: '/invite_student',
          data: JSON.stringify({
            username: username,
            class_id: class_id
          }),
          contentType: 'application/json',
          dataType: 'json'
      }).done(function() {
          location.reload();
      }).fail(function(err) {
          return modal.alert(err.responseText, 3000, true);
      });
    });
}

export function remove_student_invite(username: string, class_id: string) {
  return modal.confirm (auth.texts['delete_invite_prompt'], function () {
      $.ajax({
          type: 'POST',
          url: '/remove_student_invite',
          data: JSON.stringify({
              username: username,
              class_id: class_id
          }),
          contentType: 'application/json',
          dataType: 'json'
      }).done(function () {
          location.reload();
      }).fail(function (err) {
          return modal.alert(err.responseText, 3000, true);
      });
  });
}

export function remove_student(class_id: string, student_id: string, self_removal: boolean) {
  let confirm_text;
  if (self_removal) {
    confirm_text = auth.texts['self_removal_prompt'];
  } else {
    confirm_text = auth.texts['remove_student_prompt'];
  }
  modal.confirm (confirm_text, function () {
    $.ajax({
      type: 'DELETE',
      url: '/class/' + class_id + '/student/' + student_id,
      contentType: 'application/json',
      dataType: 'json'
    }).done(function(response) {
      if (response.achievement) {
          showAchievements(response.achievement, true, "");
      } else {
          location.reload();
      }
    }).fail(function(err) {
        modal.alert(err.responseText, 3000, true);
    });
  });
}

export function create_adventure() {
    modal.prompt (auth.texts['adventure_prompt'], '', function (adventure_name) {
        adventure_name = adventure_name.trim();
        console.log("test");
        if (!adventure_name) {
          modal.alert(auth.texts['adventure_empty'], 3000, true);
          return;
    }
    $.ajax({
      type: 'POST',
      url: '/for-teachers/create_adventure',
      data: JSON.stringify({
        name: adventure_name
      }),
      contentType: 'application/json',
      dataType: 'json'
    }).done(function(response) {
      window.location.pathname = '/for-teachers/customize-adventure/' + response.id ;
    }).fail(function(err) {
      return modal.alert(err.responseText, 3000, true);
    });
  });
}

function update_db_adventure(adventure_id: string) {
   const adventure_name = $('#custom_adventure_name').val();
   const level = $('#custom_adventure_level').val();
   const content = DOMPurify.sanitize(<string>$('#custom_adventure_content').val());
   const agree_public = $('#agree_public').prop('checked');

    $.ajax({
      type: 'POST',
      url: '/for-teachers/customize-adventure',
      data: JSON.stringify({
        id: adventure_id,
        name: adventure_name,
        level: level,
        content: content,
        public: agree_public
      }),
      contentType: 'application/json',
      dataType: 'json'
    }).done(function(response) {
      modal.alert (response.success, 3000, false);
    }).fail(function(err) {
      modal.alert(err.responseText, 3000, true);
    });
}

export function update_adventure(adventure_id: string, first_edit: boolean) {
   if (!first_edit) {
    modal.confirm (auth.texts['update_adventure_prompt'], function () {
        update_db_adventure(adventure_id);
    });
   } else {
       update_db_adventure(adventure_id);
   }
}

export function preview_adventure() {
    let content = DOMPurify.sanitize(<string>$('#custom_adventure_content').val());
    const name = <string>$('#custom_adventure_name').val();
    const level = <number>$('#custom_adventure_level').val();
    let container = $('<div>');
    container.addClass('preview border border-black px-8 py-4 text-left rounded-lg bg-gray-200 text-black');
    container.css('white-space', 'pre-wrap');
    container.css('width', '40em');
    container.html(content);

    // We have to show the modal first before we can "find" the <pre> attributes and convert them to ace editors
    modal.preview(container, name);
    for (const preview of $('.preview pre').get()) {
        $(preview).addClass('text-lg rounded');
        const exampleEditor = turnIntoAceEditor(preview, true)
        exampleEditor.setOptions({ maxLines: Infinity });
        exampleEditor.setOptions({ minLines: 2 });
        exampleEditor.setValue(exampleEditor.getValue().replace(/\n+$/, ''), -1);
        const mode = getHighlighter(level);
        exampleEditor.session.setMode(mode);
    }
}

export function delete_adventure(adventure_id: string) {
    modal.confirm(auth.texts['delete_adventure_prompt'], function () {
        $.ajax({
            type: 'DELETE',
            url: '/for-teachers/customize-adventure/' + adventure_id,
            contentType: 'application/json',
            dataType: 'json'
        }).done(function () {
            window.location.href = '/for-teachers';
        }).fail(function (err) {
            error.show(ErrorMessages['Connection_error'], JSON.stringify(err));
        });
    });
}

export function change_password_student(username: string) {
    modal.prompt ( auth.texts['enter_password'] + " " + username + ":", '', function (password) {
        modal.confirm (auth.texts['password_change_prompt'], function () {
            $.ajax({
              type: 'POST',
              url: '/auth/change_student_password',
              data: JSON.stringify({
                  username: username,
                  password: password
              }),
              contentType: 'application/json',
              dataType: 'json'
            }).done(function (response) {
              modal.alert(response.success, 3000, false);
            }).fail(function (err) {
              modal.alert(err.responseText, 3000, true);
            });
        });
    });
}

export function show_doc_section(section_key: string) {
  $(".section-button").each(function(){
       if ($(this).hasClass('blue-btn')) {
           $(this).removeClass("blue-btn");
           $(this).addClass("green-btn");
       }
   });
   if ($ ('#section-' + section_key).is (':visible')) {
       $("#button-" + section_key).removeClass("blue-btn");
       $("#button-" + section_key).addClass("green-btn");
       $ ('.section').hide ();
   } else {
     $("#button-" + section_key).removeClass("green-btn");
     $("#button-" + section_key).addClass("blue-btn");
     $('.section').hide();
     $('#section-' + section_key).toggle();
   }
}

//https://stackoverflow.com/questions/7196212/how-to-create-dictionary-and-add-key-value-pairs-dynamically?rq=1
export function save_customizations(class_id: string) {
    let levels: (string | undefined)[] = [];
    $('.level-select-button').each(function() {
        if ($(this).hasClass("green-btn")) {
            levels.push(<string>$(this).val());
        }
    });
    let adventures = {};
    $('.adventure_keys').each(function() {
        const name = <string>$(this).attr('adventure');
        // @ts-ignore
        adventures[name] = [];
    });
    $('.adventure_level_input').each(function() {
        const name = <string>$(this).attr('adventure');
        // @ts-ignore
        let current_list = adventures[name];
        if ($(this).prop("checked")) {
            current_list.push(<string>$(this).attr('level'));
            // @ts-ignore
            adventures[name] = current_list;
        }
    });
    let teacher_adventures: string[] = [];
    $('.teacher_adventures_checkbox').each(function() {
        if ($(this).prop("checked")) {
            teacher_adventures.push(<string>$(this).attr('id'));
        }
    });

    $.ajax({
      type: 'POST',
      url: '/for-teachers/customize-class/' + class_id,
      data: JSON.stringify({
          levels: levels,
          adventures: adventures,
          teacher_adventures: teacher_adventures
      }),
      contentType: 'application/json',
      dataType: 'json'
    }).done(function (response) {
      modal.alert(response.success, 3000, false);
      $('#remove_customizations_button').removeClass('hidden');
      $('#customizations_alert').addClass('hidden');
    }).fail(function (err) {
      modal.alert(err.responseText, 3000, true);
    });
}

export function remove_customizations(class_id: string) {
    modal.confirm (auth.texts['remove_customizations_prompt'], function () {
        $.ajax({
            type: 'DELETE',
            url: '/for-teachers/customize-class/' + class_id,
            contentType: 'application/json',
            dataType: 'json'
        }).done(function (response) {
            modal.alert(response.success, 3000, false);
            $('#remove_customizations_button').addClass('hidden');
            $('#customizations_alert').removeClass('hidden');
            $('.adventure_level_input').prop('checked', false);
            $('.teacher_adventures_checkbox').prop('checked', false);
            $('.level-select-button').removeClass('green-btn');
            $('.level-select-button').addClass('blue-btn');
        }).fail(function (err) {
            modal.alert(err.responseText, 3000, true);
        });
    });
}

export function select_all_levels_adventure(adventure_name: string) {
    let first_input = true;
    let checked = true;
    $('.adventure_level_input').each(function() {
        const name = <string>$(this).attr('adventure');
        if (name == adventure_name && $(this).is(":visible")) {
            if (first_input) {
                checked = $(this).prop("checked");
                first_input = false;
            }
            $(this).prop("checked", !checked);
        }
    });
}

export function select_all_level_adventures(level: string) {
    // It is not selected yet -> select all and change color
    if ($('#level_button_' + level).hasClass('blue-btn')) {
        $('.adventure_level_' + level).each(function(){
            $(this).removeClass('hidden');
            if ($(this).is(':enabled')) {
                $(this).prop("checked", true);
            }
        });
        $('#level_button_' + level).removeClass('blue-btn');
        $('#level_button_' + level).addClass('green-btn');
    } else {
        $('.adventure_level_' + level).each(function () {
            $(this).prop("checked", false);
            $(this).addClass('hidden');
        });
        $('#level_button_' + level).removeClass('green-btn');
        $('#level_button_' + level).addClass('blue-btn');
    }
}

