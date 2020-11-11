import praw
import datetime
import time
import re
import googleapiclient.discovery

SCHEDULE_TIME_SEC = 1800


def initialize_reddit():
    #TODO hide passwords/tokens from code
    return praw.Reddit(client_id='BLgzbnxQYUELfg',
                       client_secret='-DOj-weh83O0EtikUraqbHRh7PM',
                       user_agent='AMVBot:v0.0.0 (by u/Zbynasuper)',
                       username='I_Like_Good_AMVs',
                       password='AMVEditor20')


def post_feedback_megathread(subreddit_name='amv'):
    reddit = initialize_reddit()
    sub = reddit.subreddit(subreddit_name)

    with open('megathread_template.txt', mode='r', encoding='utf-8') as megathread_template:
        selftext = f'# FEEDBACK MEGATHREAD\n\n# {datetime.date.today().strftime("%B %Y")}\n\n{megathread_template.read()} '

        megathread = sub.submit(title=f'Feedback MEGAthread - {datetime.date.today().strftime("%B %Y")}',
                                selftext=selftext)

    widgets = sub.widgets
    for widget in widgets.sidebar:
        if widget.shortName == 'Megathreads':
            for button in widget:
                if 'Feedback' in button.text:
                    old_megathread = reddit.submission(url=button.url)
                    break
            break

    if old_megathread.stickied:
        old_megathread.mod.sticky(state=False)

    megathread.mod.sticky()
    megathread.mod.flair(text='Megathread', flair_template_id='23f368e6-f498-11e7-8211-0e87da16ebac')
    megathread.mod.suggested_sort(sort='new')

    sidebar_before, _, sidebar_after = sub.description.partition(f'{old_megathread.url}')
    new_sidebar = sidebar_before + megathread.url + sidebar_after
    sub.mod.update(description=new_sidebar)

    new_button = button.__dict__
    new_button['url'] = megathread.url
    new_button.pop('_reddit')
    widget.mod.update(buttons=[new_button])


def check_youtube_video_length(videoURL):
    #TODO Hide Google API token
    if '//youtu.be' in videoURL:
        _, _, videoID = videoURL.rpartition('//youtu.be/')
    elif 'youtube' in videoURL:
        _, _, videoID = videoURL.rpartition('v=')
        videoID, _, _ = videoID.partition('&')
    else:
        raise AttributeError('Link is not a youtube video.')

    youtube = googleapiclient.discovery.build('youtube', 'v3', developerKey='AIzaSyB_MKa0Zm0CcOu1GtadJCkrnzZU-m5qggM')
    request = youtube.videos().list(part='contentDetails', id=videoID)
    response = request.execute()

    duration = response['items'][0]['contentDetails']['duration']
    return duration


def regular_moderation(subreddit_name='amv'):
    subreddit = initialize_reddit().subreddit(subreddit_name)

    # Idea for polling submissions:
    # Poll one submission at a time in some interval (5 minutes) from first and save the first one (most recent) submission ID.
    # On each submission check, if it's ID is the same as previous saved ID (most recent submission from last check)
    # Once this check is true, it means we got to a submission that was checked last cycle and all after are also already checked.
    # Replace the old "most recent ID" with the new most recent submission ID to check against it on the next cycle.

    for submission in subreddit.stream.submissions():
        # If it's approved, from a moderator or approved submitter, then don't moderate it
        author = submission.author
        mod_check = subreddit.moderator(redditor=author)
        contributor_check = subreddit.contributor(redditor=author)
        if submission.approved or (mod_check.children.__len__() > 0):
            continue
        try:
            next(contributor_check)
            continue
        except StopIteration:
            pass

        # Video length checking
        # |- If submission is a link, hopefully to youtube
        if not (submission.is_self or submission.is_video):
            try:
                duration = check_youtube_video_length(submission.url)
            except AttributeError:
                submission.report('Check manually, link being shared is NOT youtube.')   #If not link to youtube, report for manual check
                log(f'Submission \"{submission.title}\" ({submission.permalink}) has been reported as the link is not Youtube.')
                continue
            except IndexError:
                removal_comment = submission.reply(f'Your submission has been removed. It seems that the Youtube video you\'ve tried to post is inacessible or you\' posted a youtube link that\'s not a video. \n \n This action was performed by a bot. If you think your submission was removed unfairly, please contact moderators with a link to this submission. Do not reply to this comment.')
                removal_comment.mod.distinguish(how='yes', sticky=True)
                submission.mod.remove()
                log(f'Submission \"{submission.title}\" ({submission.permalink}) has been removed as the Youtube video is unacessible.')
                continue
            if 'M' not in duration:
                removal_comment = submission.reply(f'Your submission has been removed, because your video is too short. Please note we accept only videos longer than one minute. \n \n This action was performed by a bot. If you think your submission was removed unfairly, please contact moderators with a link to this submission. Do not reply to this comment.')
                removal_comment.mod.distinguish(how='yes', sticky=True)
                submission.mod.remove()
                log(f'Submission \"{submission.title}\" ({submission.permalink}) has been removed as the Youtube video is too short.')
                continue
        # |- If submission is a reddit video
        elif submission.is_video:
            if submission.media['reddit_video']['duration'] <= 60:
                removal_comment = submission.reply(f'Your submission has been removed, because your video is too short. Please note we accept only videos longer than one minute. \n \n This action was performed by a bot. If you think your submission was removed unfairly, please contact moderators with a link to this submission. Do not reply to this comment.')
                removal_comment.mod.distinguish(how='yes', sticky=True)
                submission.mod.remove()
                log(f'Submission \"{submission.title}\" ({submission.permalink}) has been removed as the Reddit video is too short.')
                continue

        #Title check
        if re.findall(r'[A-Z]{5}', submission.title):
            removal_comment = submission.reply(f'Your submission has been removed because you have used too much CAPS LOCK in your title. \n \n This action was performed by a bot. If you think your submission was removed unfairly, please contact moderators with a link to this submission. Do not reply to this comment.')
            removal_comment.mod.distinguish(how='yes', sticky=True)
            submission.mod.remove()
            log(f'Submission \"{submission.title}\" ({submission.permalink}) has been removed because it had CAPS LOCK in the title.')
            continue
        elif re.findall(r'[^\sa-zA-Z0-9,.“”:;\-\'!?|\"&*+/=^_\[\]()]', submission.title):
            removal_comment = submission.reply(f'Your submission has been removed as it seems you have used non-english characters in your title. \n \n This action was performed by a bot. If you think your submission was removed unfairly, please contact moderators with a link to this submission. Do not reply to this comment.')
            removal_comment.mod.distinguish(how='yes', sticky=True)
            submission.mod.remove()
            log(f'Submission \"{submission.title}\" ({submission.permalink}) has been removed because it has special characters in the title.')
            continue

            #TODO copy other stuff from Automod
            #TODO create a single removal function to tidy up the code
            #TODO account karma/age gate


def log(log_message):
    print(log_message)
    try:
        with open('bot_logging.txt', 'a') as file:
            x = datetime.datetime.now()
            file.write(f'{x.strftime("%d %b %Y  %H:%M:%S")}  -  {log_message}\n')
    except FileNotFoundError:
        with open('bot_logging.txt', 'w+') as file:
            pass
        log(log_message)
    return True


if __name__ == '__main__':
    log('Starting up...')
    times_crashed = 0
    while True:
        try:
            regular_moderation()
        except KeyboardInterrupt:
            log('Shutting down...')
            break
        except Exception as e:
            if times_crashed <= 2:
                log(f'Crashed because of a following error: {e}.')
                log(f'Will try to restart in 5 minutes')
                time.sleep(300)
                log('Restarting...')
                continue
            else:
                log(f'Crashed because of a following error: {e}.')
                log(f'Automatic restart disabled because program has crashed {times_crashed} times since last manual check.')
                break

