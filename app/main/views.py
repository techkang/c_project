# -*- coding:utf-8 -*-
from flask import render_template, redirect, url_for, abort, flash, request, \
    current_app, make_response, send_from_directory
from flask_login import login_required, current_user
from flask_sqlalchemy import get_debug_queries
from . import main
from .forms import EditProfileForm, EditProfileAdminForm, PostForm, \
    CommentForm, HomeworkForm, CryptoForm
from .. import db
from ..models import Permission, Role, User, Post, Comment
from ..decorators import admin_required, permission_required
import random
from math import log
from xlwt import Workbook
import os
from werkzeug import secure_filename
from string import ascii_lowercase,ascii_uppercase,digits
import zipfile


@main.after_app_request
def after_request(response):
    for query in get_debug_queries():
        if query.duration >= current_app.config['FLASKY_SLOW_DB_QUERY_TIME']:
            current_app.logger.warning(
                'Slow query: %s\nParameters: %s\nDuration: %fs\nContext: %s\n'
                % (query.statement, query.parameters, query.duration,
                   query.context))
    return response


@main.route('/shutdown')
def server_shutdown():
    if not current_app.testing:
        abort(404)
    shutdown = request.environ.get('werkzeug.server.shutdown')
    if not shutdown:
        abort(500)
    shutdown()
    return 'Shutting down...'


@main.route('/', methods=['GET', 'POST'])
def index():
    form = HomeworkForm()
    crypto = CryptoForm()
    result = None
    '''if current_user.can(Permission.WRITE_ARTICLES) and \
            form.validate_on_submit():
        post = Post(body=form.body.data,
                    author=current_user._get_current_object())
        db.session.add(post)
        return redirect(url_for('.index'))'''
    if form.validate_on_submit():
        file_format = form.project.data.filename[-3:]
        if not (file_format in ['zip', 'txt', 'pdf']):
            flash('Wrong file type!', 'error')
        else:
            filename = current_user.class_no + '__' + current_user.student_number + '.' + file_format
            try:
                form.project.data.save('homework_' + form.times.data + '/' + filename)
                post = Post(body='I submit my homework in format ' + file_format + '.',
                            author_id=current_user.id)
                u = User.query.filter_by(id=current_user.id).first()
                u.location = "1"
                db.session.add(u)
                db.session.add(post)
                db.session.commit()
                flash("Your project has been submitted!")
            except:
                flash("Submit homework failed!")
    else:
        filename = None
    if crypto.validate_on_submit():
        result = []
        password = crypto.password.data
        count=complexity(password)
        result.append(count)
        result.append(count / (2.24385 * 10 ** (14)))
        prob=conut_prob(password)
        result.append(prob[0])
        result.append(prob[1])
        if prob[0]==0:
            result.append(10)
        else:
            result.append(log(prob[0]/prob[1]))
        for i in range(5):
            result[i]='%.3e'%(result[i])
        result[4]=result[4][:5]


    admin = False
    page = request.args.get('page', 1, type=int)
    show_followed = False
    query = Post.query
    if current_user.can(Permission.MODERATE_COMMENTS):
        # query = Post.query
        admin = True
    else:
        if not (current_user.is_authenticated):
            #           query=Post.query.filter_by(author_id=current_user.id)
            #       else:
            query = Post.query.filter_by(id=-1)
    pagination = query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'], error_out=False)
    posts = pagination.items
    return render_template('index.html', form=form, posts=posts,
                           show_followed=show_followed, pagination=pagination, admin=admin,result=result,crypto=crypto)


@main.route('/excel')
def excel():
    workbook = Workbook()
    sheet = workbook.add_sheet('Sheet1')
    users = User.query.filter_by(role=Role.query.filter_by(name='User').first()).all()
    rowlen = len(users)
    tag = ['id', 'email', 'student number', 'name', 'submitted']
    for j in range(5):
        sheet.write(0, j, tag[j])
    for i in range(0, rowlen):
        user = []
        user.append(users[i].id)
        user.append(users[i].email)
        user.append(users[i].student_number)
        user.append(users[i].username)
        user.append(users[i].location)
        for j in range(5):
            sheet.write(i + 1, j, user[j])
    workbook.save('student.xls')
    return redirect(url_for('.download'))


@main.route('/download')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def download():
    filename = 'student.xls'
    directory = os.getcwd()  # 假设在当前目录
    return send_from_directory(directory, filename, as_attachment=True)


@main.route('/download_homework')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def download_homework():
    files = os.listdir('homework')
    homework_zip = zipfile.ZipFile('homework_zip.zip', 'w')
    for file in files:
        homework_zip.write(os.path.join('homework', file), file, compress_type=zipfile.ZIP_DEFLATED)
    homework_zip.close()
    return send_from_directory(os.getcwd(), 'homework_zip.zip', as_attachment=True)


@main.route('/user/<username>')
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    pagination = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    return render_template('user.html', user=user, posts=posts,
                           pagination=pagination)


@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.phone = form.phone.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user)
        flash('Your profile has been updated.')
        return redirect(url_for('.user', username=current_user.username))
    form.phone.data = current_user.phone
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)


@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        flash('The profile has been updated.')
        return redirect(url_for('.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form, user=user)


@main.route('/delete_user/<int:id>')
@login_required
@admin_required
def delete_user_admin(id):
    user = User.query.get_or_404(id)
    username = user.username
    user_id = user.id
    posts = Post.query.filter_by(author_id=user_id).all()
    for post in posts:
        db.session.delete(post)
    db.session.delete(user)
    flash('User ' + username + ' has been deleted!')
    return redirect(url_for('.index'))


@main.route('/moderate')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate():
    page = request.args.get('page', 1, type=int)
    pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    return render_template('moderate.html', comments=comments,
                           pagination=pagination, page=page)


@main.route('/post/<int:id>', methods=['GET', 'POST'])
def post(id):
    post = Post.query.get_or_404(id)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(body=form.body.data,
                          post=post,
                          author=current_user._get_current_object())
        db.session.add(comment)
        flash('Your comment has been published.')
        return redirect(url_for('.post', id=post.id, page=-1))
    page = request.args.get('page', 1, type=int)
    if page == -1:
        page = (post.comments.count() - 1) // \
               current_app.config['FLASKY_COMMENTS_PER_PAGE'] + 1
    pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(
        page, per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    return render_template('post.html', posts=[post], form=form,
                           comments=comments, pagination=pagination)


@main.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    post = Post.query.get_or_404(id)
    if current_user != post.author and \
            not current_user.can(Permission.ADMINISTER):
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.body = form.body.data
        db.session.add(post)
        flash('The post has been updated.')
        return redirect(url_for('.post', id=post.id))
    form.body.data = post.body
    return render_template('edit_post.html', form=form)


@main.route('/follow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    if current_user.is_following(user):
        flash('You are already following this user.')
        return redirect(url_for('.user', username=username))
    current_user.follow(user)
    flash('You are now following %s.' % username)
    return redirect(url_for('.user', username=username))


@main.route('/unfollow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    if not current_user.is_following(user):
        flash('You are not following this user.')
        return redirect(url_for('.user', username=username))
    current_user.unfollow(user)
    flash('You are not following %s anymore.' % username)
    return redirect(url_for('.user', username=username))


@main.route('/followers/<username>')
def followers(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followers.paginate(
        page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.follower, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followers of",
                           endpoint='.followers', pagination=pagination,
                           follows=follows)


@main.route('/followed-by/<username>')
def followed_by(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followed.paginate(
        page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.followed, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followed by",
                           endpoint='.followed_by', pagination=pagination,
                           follows=follows)


@main.route('/all')
@login_required
def show_all():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed', '', max_age=30 * 24 * 60 * 60)
    return resp


@main.route('/followed')
@login_required
def show_followed():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed', '1', max_age=30 * 24 * 60 * 60)
    return resp


@main.route('/moderate/enable/<int:id>')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate_enable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = False
    db.session.add(comment)
    return redirect(url_for('.moderate',
                            page=request.args.get('page', 1, type=int)))


@main.route('/moderate/disable/<int:id>')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate_disable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = True
    db.session.add(comment)
    return redirect(url_for('.moderate',
                            page=request.args.get('page', 1, type=int)))


def complexity(password):
    password_list = [password]
#    password_list = ['Myteacherislwh17', 'ustchhhh']
    for password in password_list:
        length = len(password)

        def alpha_and_num(str, case):
            for x in str:
                if not (x in case or x in digits):
                    return False
            return True

        count = 0
        fail = 0
        flag = 0
        with open('rockyou.txt') as rockyou:
            row = 'test'
            while count != 14344380:
                count += 1
                try:
                    row = rockyou.readline().strip()
                    if row == password:
                        flag = 1
                        print('your password was found in rockyou.txt!')
                        break
                except:
                    fail += 1
        if flag == 0:
            count += 26 ** length
            if not (password.islower() and password.isalpha()):
                count += 26 ** length
                if not password.isupper():
                    count += 10 ** length
                    if not password.isdecimal():
                        for i in range(length + 1):
                            count += 26 ** i * (10 ** (length - i))
                        if not alpha_and_num(password, ascii_lowercase):
                            for i in range(length + 1):
                                count += 26 ** i * (10 ** (length - i))
                            if not alpha_and_num(password, ascii_uppercase):
                                count += 56 ** length
        return count


freq_dict={'aa': 0.00011409678973294032, 'ab': 0.0019512802954656473, 'ac': 0.003634958580801076, 'ad': 0.004409991050533055,
     'ae': 3.434163243606592e-05, 'af': 0.000904892631730655, 'ag': 0.00246396521248932, 'ah': 0.0005198159663819815,
     'ai': 0.004580385598357907, 'aj': 6.924624245305096e-05, 'ak': 0.001372914660668078, 'al': 0.006222215883511682,
     'am': 0.002187543220258035, 'an': 0.013575453727089862, 'ao': 6.117689712654367e-05, 'ap': 0.002117734000224065,
     'aq': 4.259863695621292e-05, 'ar': 0.010740486288774847, 'as': 0.009426121296522356, 'at': 0.009953068312262647,
     'au': 0.0009418614928776768, 'av': 0.0018450651918655745, 'aw': 0.0011298960049046607, 'ax': 5.723605406010987e-05,
     'ay': 0.00199387893242186, 'az': 0.00019009876315702063, 'ba': 0.0016108665182032232, 'bb': 0.0003269023153203652,
     'bc': 7.881686132867588e-06, 'bd': 1.5200394684816063e-05, 'be': 0.004615665526762172,
     'bf': 1.0133596456544041e-05, 'bg': 1.3136143554779314e-06, 'bh': 1.632634984665429e-05,
     'bi': 0.0007014700658252153, 'bj': 6.080157873926425e-05, 'bk': 1.125955161838227e-06, 'bl': 0.0022250750589859762,
     'bm': 2.4395695173161582e-05, 'bn': 6.005094196470544e-06, 'bo': 0.0018683349318768978,
     'bp': 5.066798228272021e-06, 'bq': 1.876591936397045e-07, 'br': 0.0009024530622133389, 'bs': 0.0007958626402259867,
     'bt': 6.342880745022012e-05, 'bu': 0.0018711498197814935, 'bv': 3.396631404878651e-05, 'bw': 1.463741710389695e-05,
     'bx': 0.0, 'by': 0.0007097270703453623, 'bz': 1.876591936397045e-07, 'ca': 0.002843412102028802,
     'cb': 2.4958672754080696e-05, 'cc': 0.00023363569608143207, 'cd': 3.190206291874976e-05,
     'ce': 0.003210661143981704, 'cf': 1.632634984665429e-05, 'cg': 0.00011691167763753589, 'ch': 0.003726911585684531,
     'ci': 0.000932853851582971, 'cj': 4.503820647352908e-06, 'ck': 0.002371824548412225, 'cl': 0.0012079622294587776,
     'cm': 2.889951582051449e-05, 'cn': 1.4449757910257246e-05, 'co': 0.0039900097751673965,
     'cp': 2.308208081768365e-05, 'cq': 5.44211661555143e-06, 'cr': 0.0012175328483344026, 'cs': 9.758278069264633e-05,
     'ct': 0.0013556500148532251, 'cu': 0.0007677137611800311, 'cv': 5.254457421911726e-06, 'cw': 4.466288808624967e-05,
     'cx': 3.75318387279409e-07, 'cy': 0.00013943078087430043, 'cz': 1.876591936397045e-07, 'da': 0.004400795750044709,
     'db': 0.0017213977832570091, 'dc': 0.0007609580302090017, 'dd': 0.0015072786433141063, 'de': 0.005348099359537938,
     'df': 0.001007729869845213, 'dg': 0.0008378982996012805, 'dh': 0.004066011748591477, 'di': 0.0049382516806288235,
     'dj': 0.0002878692030433067, 'dk': 0.0001471248078135283, 'dl': 0.0013027301222468285, 'dm': 0.0011541040408841825,
     'dn': 0.001561512150275981, 'do': 0.004650570136779156, 'dp': 0.0007361870166485607, 'dq': 8.819982101066111e-05,
     'dr': 0.0017608062139213472, 'ds': 0.003013243672272735, 'dt': 0.005089692649896065, 'du': 0.0016067380159431497,
     'dv': 0.0003026942793408433, 'dw': 0.0016493366528993628, 'dx': 6.568071777389657e-06, 'dy': 0.0010488272332523083,
     'dz': 1.0321255650183746e-05, 'ea': 0.010290479542426834, 'eb': 0.0020984051032791754, 'ec': 0.004199812753656587,
     'ed': 0.015328190595684701, 'ee': 0.004713435966648458, 'ef': 0.002625164459825826, 'eg': 0.0016759842583962006,
     'eh': 0.0038053531286259277, 'ei': 0.0033621021132489454, 'ej': 0.00035354992081720323,
     'ek': 0.0005066798228272021, 'el': 0.005640660042422237, 'em': 0.004257236466910336, 'en': 0.00902377998535883,
     'eo': 0.002813761949433729, 'ep': 0.002473348172171305, 'eq': 0.00020060767800084408, 'er': 0.01630570733535392,
     'es': 0.010714214001665287, 'et': 0.008037443263588543, 'eu': 0.0004353693292441144, 'ev': 0.002571306271251231,
     'ew': 0.005117090892167462, 'ex': 0.0010681561301971979, 'ey': 0.003335079189364828, 'ez': 6.230285228838189e-05,
     'fa': 0.00186702131752142, 'fb': 0.00017602432363404282, 'fc': 0.00024039142705246144,
     'fd': 0.00013811716651882249, 'fe': 0.001979992152092522, 'ff': 0.001309298194024218, 'fg': 0.00010752871795555067,
     'fh': 0.0007341227655185239, 'fi': 0.0022252627181796156, 'fj': 4.072204501981587e-05,
     'fk': 1.8202941783051335e-05, 'fl': 0.0009467406319123091, 'fm': 0.00027867390255496117,
     'fn': 6.249051148202159e-05, 'fo': 0.003319315817099093, 'fp': 0.00016889327427573403, 'fq': 7.881686132867588e-06,
     'fr': 0.0017337832900372297, 'fs': 0.0003640588356610267, 'ft': 0.0025097540557374076, 'fu': 0.0008031813487779352,
     'fv': 3.0213130175992422e-05, 'fw': 0.0002529645930263216, 'fx': 2.064251130036749e-06,
     'fy': 0.00025653011770547605, 'fz': 1.3136143554779314e-06, 'ga': 0.0026394265585424435,
     'gb': 0.00036912563388929873, 'gc': 0.0002225638036566895, 'gd': 0.0002426433373761379,
     'ge': 0.0029691437617674044, 'gf': 0.0003770073200221663, 'gg': 0.0005579107826908414, 'gh': 0.00402604034034622,
     'gi': 0.001802278895715722, 'gj': 4.897904953996287e-05, 'gk': 2.139314807492631e-05, 'gl': 0.0008335821381475673,
     'gm': 0.0003700639298574972, 'gn': 0.0004522586566716878, 'go': 0.002676770738076745, 'gp': 0.00019554087977257208,
     'gq': 2.176846646220572e-05, 'gr': 0.0018882268064027066, 'gs': 0.0009649435736953604, 'gt': 0.0018931059454373388,
     'gu': 0.0006541799490280098, 'gv': 6.005094196470543e-05, 'gw': 0.0006477995364442599,
     'gx': 1.3136143554779314e-06, 'gy': 0.0002263169875294836, 'gz': 3.7531838727940894e-06,
     'ha': 0.013758046122501295, 'hb': 0.00016532774959657966, 'hc': 0.0001465618302326092,
     'hd': 0.00014093205442341805, 'he': 0.02816201518951045, 'hf': 0.00015388053878455767, 'hg': 9.063939052797726e-05,
     'hh': 0.0006735088459728993, 'hi': 0.0091318716808953, 'hj': 5.742371325374957e-05, 'hk': 2.3645058398602765e-05,
     'hl': 0.00019403960622345443, 'hm': 0.00028693090707510813, 'hn': 0.00015632010830187384,
     'ho': 0.0051405482913724244, 'hp': 0.00012216613505944762, 'hq': 1.0321255650183746e-05,
     'hr': 0.0009135249546380815, 'hs': 0.0004653948002264671, 'ht': 0.0027812969089340603, 'hu': 0.0006558688817707672,
     'hv': 3.1339085337830646e-05, 'hw': 0.00032089722112389464, 'hx': 7.50636774558818e-07,
     'hy': 0.0004526339750589672, 'hz': 7.50636774558818e-07, 'ia': 0.0008945713760804713, 'ib': 0.00048284710523495964,
     'ic': 0.0030432691432550874, 'id': 0.005555650427703451, 'ie': 0.00186702131752142, 'if': 0.0012257898528545497,
     'ig': 0.0022794962251414903, 'ih': 0.0002809258128786376, 'ii': 7.731558777955825e-05, 'ij': 3.565524679154385e-05,
     'ik': 0.0008791833222020155, 'il': 0.003237308749478542, 'im': 0.0033791790998701585, 'in': 0.019065986414600337,
     'io': 0.0027906798686160453, 'ip': 0.0005847460473813192, 'iq': 2.4771013560440992e-05, 'ir': 0.002496242593795349,
     'is': 0.007247210399171747, 'it': 0.008139342205734902, 'iu': 0.00023776419834150558, 'iv': 0.0011846924894474543,
     'iw': 0.0005449622983297018, 'ix': 0.00024095440463338055, 'iy': 1.1634870005661677e-05,
     'iz': 0.0004905411321741875, 'ja': 0.0001722711397612487, 'jb': 0.0, 'jc': 3.75318387279409e-07, 'jd': 0.0,
     'je': 0.00018540728331602804, 'jf': 1.876591936397045e-07, 'jg': 0.0, 'jh': 1.876591936397045e-07,
     'ji': 2.308208081768365e-05, 'jj': 9.382959681985224e-07, 'jk': 5.629775809191135e-07, 'jl': 0.0, 'jm': 0.0,
     'jn': 0.0, 'jo': 0.0009403602193285591, 'jp': 1.876591936397045e-07, 'jq': 0.0, 'jr': 1.8765919363970447e-06,
     'js': 3.75318387279409e-07, 'jt': 0.0, 'ju': 0.0007555159135934502, 'jv': 0.0, 'jw': 1.876591936397045e-07,
     'jx': 0.0, 'jy': 0.0, 'jz': 0.0, 'ka': 0.0007853537253821632, 'kb': 0.00012723293328771964,
     'kc': 7.806622455411706e-05, 'kd': 9.23283232707346e-05, 'ke': 0.0037665076755425088, 'kf': 0.000142245668778896,
     'kg': 5.085564147635991e-05, 'kh': 0.0003603056517882326, 'ki': 0.0018199188599178542, 'kj': 1.876591936397045e-05,
     'kk': 2.9837811788713012e-05, 'kl': 0.000330843158386799, 'km': 0.0001005853277908816, 'kn': 0.0009750771701519045,
     'ko': 0.0004021536519698867, 'kp': 7.450069987496268e-05, 'kq': 8.81998210106611e-06, 'kr': 0.00016026095136830763,
     'ks': 0.0006742594827474582, 'kt': 0.0005732988365692972, 'ku': 0.00010358787488911688,
     'kv': 1.3323802748419018e-05, 'kw': 0.00027041689803481415, 'kx': 3.75318387279409e-07,
     'ky': 0.00024376929253797612, 'kz': 2.064251130036749e-06, 'la': 0.0036497836570986123,
     'lb': 0.0004179170242356219, 'lc': 0.00028618027030054933, 'ld': 0.0034069526605288347, 'le': 0.007850910025110677,
     'lf': 0.0010197400582381542, 'lg': 0.00016551540879021934, 'lh': 0.0004753407374893715, 'li': 0.004576820073678753,
     'lj': 5.2169255831837846e-05, 'lk': 0.00047477775990845236, 'll': 0.006430517588451754,
     'lm': 0.0004025289703571661, 'ln': 0.00013192441312871226, 'lo': 0.004258925399653093, 'lp': 0.0003683749971147399,
     'lq': 1.0508914843823452e-05, 'lr': 0.0003019436425662845, 'ls': 0.0010786650450410214, 'lt': 0.001304982032570505,
     'lu': 0.0008887539410776405, 'lv': 0.0002542782073817996, 'lw': 0.0004824717868476802, 'lx': 3.75318387279409e-07,
     'ly': 0.004178982583162579, 'lz': 4.128502260073498e-06, 'ma': 0.003904812501254971, 'mb': 0.0012222243281753953,
     'mc': 0.0002512756602835643, 'md': 0.00010358787488911688, 'me': 0.005530316436562091,
     'mf': 0.00021130425203830724, 'mg': 0.0001255440005449623, 'mh': 0.0004858496523331949,
     'mi': 0.0030276934301829922, 'mj': 4.1285022600734986e-05, 'mk': 2.0642511300367493e-05,
     'ml': 0.00013999375845521954, 'mm': 0.0004987981366943345, 'mn': 0.0001546311755591165, 'mo': 0.002814324927014648,
     'mp': 0.0012590055301287774, 'mq': 6.192753390110248e-06, 'mr': 0.00046633309619466566,
     'ms': 0.0009073322012479711, 'mt': 0.0008682990889709127, 'mu': 0.0009951567038713528, 'mv': 2.683526469047774e-05,
     'mw': 0.00035561417194724, 'mx': 7.50636774558818e-07, 'my': 0.0010133596456544042, 'mz': 1.8765919363970447e-06,
     'na': 0.003528180499620084, 'nb': 0.0005273223341275696, 'nc': 0.002052991578418367, 'nd': 0.010749493930069551,
     'ne': 0.006690800890030024, 'nf': 0.0007731558777955825, 'ng': 0.010665234952125326, 'nh': 0.0017397883842337003,
     'ni': 0.0029918505241978087, 'nj': 0.00019798044928988822, 'nk': 0.0009563112507879341,
     'nl': 0.0008360217076648834, 'nm': 0.0005346410426795181, 'nn': 0.0008831241652684493, 'no': 0.00482002638863581,
     'np': 0.0003700639298574972, 'nq': 3.603056517882326e-05, 'nr': 0.00032521338257760786,
     'ns': 0.0029721463088656394, 'nt': 0.010076548061677572, 'nu': 0.0005106206658936358, 'nv': 0.0003086993735373139,
     'nw': 0.0009185917528663534, 'nx': 4.1285022600734986e-05, 'ny': 0.0012837765436892184,
     'nz': 2.139314807492631e-05, 'oa': 0.001255440005449623, 'ob': 0.0020030742329102055, 'oc': 0.0010842948208502124,
     'od': 0.0018208571558860525, 'oe': 0.0004590143876427172, 'of': 0.0057496900339269056, 'og': 0.0009653188920826398,
     'oh': 0.001390179306482931, 'oi': 0.0016380771012809805, 'oj': 9.589384794988899e-05, 'ok': 0.0019920023404854633,
     'ol': 0.002553853966242738, 'om': 0.004274313453531549, 'on': 0.010893616190784845, 'oo': 0.004209195713338571,
     'op': 0.0017844512723199498, 'oq': 2.1580807268566017e-05, 'or': 0.00852854737334365, 'os': 0.002727438720359465,
     'ot': 0.005456941691848967, 'ou': 0.01124679079321477, 'ov': 0.0012657612610998067, 'ow': 0.004650570136779156,
     'ox': 9.101470891525668e-05, 'oy': 0.0008309549094366115, 'oz': 0.00010996828747286683,
     'pa': 0.0021712168704113807, 'pb': 0.0001047138300509551, 'pc': 4.466288808624967e-05, 'pd': 2.965015259507331e-05,
     'pe': 0.0034591219163606726, 'pf': 6.868326487213184e-05, 'pg': 1.9891874525808676e-05, 'ph': 0.000572735858988378,
     'pi': 0.0012779591086863875, 'pj': 1.2010188392941088e-05, 'pk': 1.426209871661754e-05,
     'pl': 0.0017521738910139207, 'pm': 7.055985680852888e-05, 'pn': 2.6272287109558626e-05, 'po': 0.002005513802427522,
     'pp': 0.0015553193968858708, 'pq': 6.380412583749952e-06, 'pr': 0.001858013676226714, 'ps': 0.00044756717683069517,
     'pt': 0.0009015147662451403, 'pu': 0.0008091864429744057, 'pv': 7.881686132867588e-06,
     'pw': 0.00013905546248702103, 'px': 0.0, 'py': 0.00015969797378738852, 'pz': 5.254457421911726e-06,
     'qa': 3.75318387279409e-07, 'qb': 0.0, 'qc': 1.876591936397045e-07, 'qd': 0.0, 'qe': 1.876591936397045e-07,
     'qf': 0.0, 'qg': 0.0, 'qh': 3.75318387279409e-07, 'qi': 1.876591936397045e-07, 'qj': 0.0, 'qk': 0.0, 'ql': 0.0,
     'qm': 3.75318387279409e-07, 'qn': 0.0, 'qo': 0.0, 'qp': 0.0, 'qq': 0.0, 'qr': 0.0, 'qs': 0.0,
     'qt': 3.75318387279409e-07, 'qu': 0.0008120013308790013, 'qv': 0.0, 'qw': 1.876591936397045e-07, 'qx': 0.0,
     'qy': 0.0, 'qz': 0.0, 'ra': 0.004364577525672247, 'rb': 0.0006740718235538185, 'rc': 0.0009720746230536692,
     'rd': 0.0021167957042558666, 're': 0.0129923966124513, 'rf': 0.000759456756659884, 'rg': 0.0007639605773072369,
     'rh': 0.0012948484361139608, 'ri': 0.005097949654416212, 'rj': 9.683214391808751e-05, 'rk': 0.0008827488468811698,
     'rl': 0.0008733658871991846, 'rm': 0.0021821011036424836, 'rn': 0.0013952461047112028, 'ro': 0.007100273250551859,
     'rp': 0.0005909388007714294, 'rq': 3.903311227705853e-05, 'rr': 0.004209571031725851, 'rs': 0.003670989145979899,
     'rt': 0.003992824663071992, 'ru': 0.0010272464259837423, 'rv': 0.00034548057549069596, 'rw': 0.0010131719864607644,
     'rx': 2.814887904595567e-06, 'ry': 0.005130602354109521, 'rz': 3.940843066433794e-06, 'sa': 0.006601099795470245,
     'sb': 0.0011272687761937049, 'sc': 0.0018039678284584792, 'sd': 0.0007037219761488918, 'se': 0.0062000720986621965,
     'sf': 0.0012569412789987407, 'sg': 0.000587373276092275, 'sh': 0.005246951054166137, 'si': 0.004499879804286473,
     'sj': 0.00022331444043124834, 'sk': 0.000883311824462089, 'sl': 0.0018414996671864202, 'sm': 0.0013271258174199902,
     'sn': 0.001575586589798959, 'so': 0.004382405149068019, 'sp': 0.0020102052822685143, 'sq': 0.00016532774959657966,
     'sr': 0.0005774273388293707, 'ss': 0.00443851524796629, 'st': 0.010348466233261504, 'su': 0.00163188434789087,
     'sv': 0.00023344803688779239, 'sw': 0.002329788889036931, 'sx': 3.190206291874976e-06,
     'sy': 0.00045150801989712896, 'sz': 8.257004520146997e-06, 'ta': 0.005200223914949851, 'tb': 0.0010154238967844409,
     'tc': 0.0012644476467443288, 'td': 0.0007688397163418693, 'te': 0.007636790885167774, 'tf': 0.0007414414740704725,
     'tg': 0.0003777579567967251, 'th': 0.028832709147578756, 'ti': 0.006469550700728812, 'tj': 0.00019835576767716762,
     'tk': 0.00023757653914786587, 'tl': 0.0017281535142280385, 'tm': 0.0010482642556713891,
     'tn': 0.0004556365221572025, 'to': 0.011509326005116716, 'tp': 0.0005269470157402902, 'tq': 5.235691502547755e-05,
     'tr': 0.002756713554567259, 'ts': 0.003849453039131258, 'tt': 0.005696582482126869, 'tu': 0.0016585319533877082,
     'tv': 0.00013811716651882249, 'tw': 0.00279405773410156, 'tx': 7.13104935830877e-06, 'ty': 0.0012732676288453948,
     'tz': 6.380412583749952e-05, 'ua': 0.0006252804332074954, 'ub': 0.00039108175954514417,
     'uc': 0.0010713463364890729, 'ud': 0.0009835218338656911, 'ue': 0.0006671284333891495,
     'uf': 0.00026591307738746124, 'ug': 0.0019068050665730371, 'uh': 0.00022087487091393217,
     'ui': 0.0008414638242804349, 'uj': 2.045485210672779e-05, 'uk': 0.00016438945362838112, 'ul': 0.003144792767014168,
     'um': 0.001296725028050358, 'un': 0.0030738575918183592, 'uo': 6.605603616117597e-05, 'up': 0.0015746482938307604,
     'uq': 1.3136143554779314e-06, 'ur': 0.00363233135209012, 'us': 0.0037614408773142365, 'ut': 0.004414682530374048,
     'uu': 2.4395695173161582e-05, 'uv': 7.99428164905141e-05, 'uw': 0.0002465841804425717, 'ux': 6.155221551382307e-05,
     'uy': 9.23283232707346e-05, 'uz': 2.270676243040424e-05, 'va': 0.0004308655085967615, 'vb': 1.125955161838227e-06,
     'vc': 3.377865485514681e-06, 'vd': 1.8765919363970447e-06, 've': 0.006406121893278592, 'vf': 3.75318387279409e-07,
     'vg': 1.6889327427573404e-06, 'vh': 1.125955161838227e-06, 'vi': 0.0012066486151032997, 'vj': 3.75318387279409e-07,
     'vk': 1.876591936397045e-07, 'vl': 1.501273549117636e-06, 'vm': 1.125955161838227e-06,
     'vn': 1.3136143554779314e-06, 'vo': 0.0007380636085849578, 'vp': 5.629775809191135e-07, 'vq': 0.0,
     'vr': 6.568071777389657e-06, 'vs': 9.382959681985224e-06, 'vt': 2.439569517316158e-06, 'vu': 8.444663713786702e-06,
     'vv': 4.691479840992612e-06, 'vw': 5.629775809191135e-07, 'vx': 0.0, 'vy': 4.804075357176435e-05, 'vz': 0.0,
     'wa': 0.007320960462272152, 'wb': 9.814575827356544e-05, 'wc': 0.00010171128295271982,
     'wd': 0.00020586213542275582, 'we': 0.003907815048353206, 'wf': 7.900452052231559e-05, 'wg': 3.377865485514681e-05,
     'wh': 0.004066199407785117, 'wi': 0.0034039501134305998, 'wj': 1.6514009040293994e-05,
     'wk': 4.2035659375293806e-05, 'wl': 0.0003177070148320197, 'wm': 0.00014993969571812387,
     'wn': 0.0009146509097999197, 'wo': 0.002323033158065902, 'wp': 6.774496890393332e-05, 'wq': 8.257004520146997e-06,
     'wr': 0.0002722934899712112, 'ws': 0.0004582637508681583, 'wt': 0.0004956079304024595, 'wu': 5.235691502547755e-05,
     'wv': 2.3832717592242468e-05, 'ww': 0.0003227738130602917, 'wx': 3.75318387279409e-07,
     'wy': 0.00012291677183400644, 'wz': 5.629775809191135e-07, 'xa': 0.00018559494250966772,
     'xb': 2.3269740011323355e-05, 'xc': 0.0001884098304142633, 'xd': 6.568071777389657e-06,
     'xe': 0.00014130737281069748, 'xf': 1.8202941783051335e-05, 'xg': 3.190206291874976e-06,
     'xh': 3.997140824525705e-05, 'xi': 0.00012460570457676378, 'xj': 9.382959681985224e-07, 'xk': 7.50636774558818e-07,
     'xl': 2.2894421624043948e-05, 'xm': 1.088423323110286e-05, 'xn': 4.503820647352908e-06,
     'xo': 2.420803597952188e-05, 'xp': 0.0003477324858143724, 'xq': 1.3136143554779314e-06,
     'xr': 5.817435002830839e-06, 'xs': 2.9462493401433605e-05, 'xt': 0.0003661230867910634,
     'xu': 6.943390164669066e-06, 'xv': 1.125955161838227e-06, 'xw': 2.552165033499981e-05,
     'xx': 1.3136143554779314e-06, 'xy': 8.81998210106611e-06, 'xz': 1.876591936397045e-07, 'ya': 0.0016816140342053919,
     'yb': 0.0008360217076648834, 'yc': 0.0007174210972845902, 'yd': 0.0006444216709587452, 'ye': 0.0018146644024959423,
     'yf': 0.0008279523623383762, 'yg': 0.00036593542759742374, 'yh': 0.0014571736386123054,
     'yi': 0.0014271481676299525, 'yj': 0.0001463741710389695, 'yk': 0.0001338010050651093, 'yl': 0.0006658148190336715,
     'ym': 0.0005629775809191135, 'yn': 0.0003571154454963576, 'yo': 0.004155525183957616, 'yp': 0.0005609133297890767,
     'yq': 5.535946212371282e-05, 'yr': 0.0005301372220321652, 'ys': 0.002340485463074394, 'yt': 0.0019769896049942866,
     'yu': 0.0001426209871661754, 'yv': 0.00010827935473010949, 'yw': 0.001529234768969952, 'yx': 2.064251130036749e-06,
     'yy': 0.0002430186557634173, 'yz': 8.444663713786702e-06, 'za': 0.00024376929253797612,
     'zb': 3.002547098235272e-06, 'zc': 1.3136143554779314e-06, 'zd': 5.629775809191135e-07,
     'ze': 0.0004062821542299602, 'zf': 3.0025470982352715e-05, 'zg': 1.6889327427573404e-06,
     'zh': 3.002547098235272e-06, 'zi': 0.00011916358796121235, 'zj': 5.629775809191135e-07,
     'zk': 2.9462493401433605e-05, 'zl': 2.4020376785882175e-05, 'zm': 5.066798228272021e-06,
     'zn': 5.066798228272021e-05, 'zo': 3.828247550249972e-05, 'zp': 9.382959681985224e-07, 'zq': 0.0,
     'zr': 1.501273549117636e-06, 'zs': 4.128502260073498e-06, 'zt': 3.002547098235272e-06,
     'zu': 3.7531838727940894e-06, 'zv': 1.876591936397045e-07, 'zw': 5.254457421911726e-06, 'zx': 0.0,
     'zy': 3.640588356610267e-05, 'zz': 4.6727139216286416e-05, 'a': 0.08054032336306292, 'b': 0.01588816562950558,
     'c': 0.022412137496389907, 'd': 0.04900494650868515, 'e': 0.12101522122485531, 'f': 0.019574542829363935,
     'g': 0.024166187979340226, 'h': 0.06403663557841911, 'i': 0.06629774120258392, 'j': 0.002081515775851602,
     'k': 0.011204755133839474, 'l': 0.04247346827405524, 'm': 0.024433039352695883, 'n': 0.06481129272976381,
     'o': 0.07709884141090438, 'p': 0.01751929934062189, 'q': 0.0008142532412026778, 'r': 0.06159331287723017,
     's': 0.06045853773329087, 't': 0.08630146060780186, 'u': 0.02865161802571644, 'v': 0.008876467518351661,
     'w': 0.024806293488845256, 'x': 0.0015896610293219366, 'y': 0.02329150847778556, 'z': 0.0010587731705152127}

def cal_pertinence(word):
    probability = 1
    for i in range(len(word) - 1):
        probability *= freq_dict[word[i:i + 2]]
    return probability


def cal_markov(word):
    probability = cal_pertinence(word)
    for i in word[1:]:
        probability /= freq_dict[i]
    return probability

def conut_prob(password):
    passwordlist=[password.lower()]
    for origin_password in passwordlist:
        password = ""
        for x in origin_password:
            if (x in ascii_lowercase):
                password += x

        random_str = ""
        for i in range(0, len(password)):
            random_str += random.choice(ascii_lowercase)
        return cal_markov(password),(1.0/26)**len(password)

