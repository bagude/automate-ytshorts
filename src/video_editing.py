from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip
from moviepy.config import change_settings
from moviepy.video.tools.subtitles import SubtitlesClip

def create_shorts(
        video_fp: str,
        background_music_fp: str,
        tts_audio_fp: str,
        output_fp: str,
        text: str
):

    # load video and adjust size of video
    video = VideoFileClip(video_fp)

    width, height = video.size
    target_width = 1080
    target_height = 1920

    x_center = width / 2 
    new_width = height * 9 / 16
    x_start = x_center - new_width / 2
    x_end = x_center + new_width / 2

    cropped_video = video.crop(x1=x_start, x2=x_end)
    final_video = cropped_video.resize((target_width, target_height))

    # load background music
    bg_music = AudioFileClip(background_music_fp)
    tts_audio = AudioFileClip(tts_audio_fp)

    if bg_music.duration > final_video.duration:
        bg_music = bg_music.subclip(0, final_video.duration)
    else:
        bg_music = bg_music.loop(duration=final_video.duration)

    bg_music = bg_music.volumex(0.3)

    # combine audio
    final_audio = CompositeVideoClip([bg_music.set_start(0), tts_audio.set_start(0)]).audio

    # get text
    txt_clip = TextClip(
        text,
        font = 'Arial',
        fontsize = 70,
        color = 'yellow',
        stroke_color = 'black',
        stroke_width = 2,
        size = (target_width * 0.8, None),
        method = 'caption'
    ).set_position(('center', 100))

    subtitle_timing = [
        ("Frirst subtitle", 0, 2),
        ("Second subtitle", 2, 4),
        ("Third subtitle", 4, 6)
    ]

    subtitle_clips = [
        create_subtitles(text, start, end, target_width) for text, start, end in subtitle_timing
    ]

    final = CompositeVideoClip([final_video, txt_clip, *subtitle_clips]).set_audio(final_audio)
    final.write_videofile(output_fp, codec='libx264', audio_codec='aac', fps =  30)

    video.close()
    bg_music.close()
    tts_audio.close()
    final.close()

    return final
    
def create_subtitles(text, start, end, target_width):
    subtitle_clip = (TextClip(
        text,
        font = 'Arial',
        fontsize = 50,
        color = 'white',
        stroke_color = 'black',
        stroke_width = 2,
        size = (target_width * 0.8, None),
        method = 'caption')
    .set_start(start)
    .set_end(end)
    .set_position(('center', 'bottom')))
    return subtitle_clip

def main():
    pass

if __name__ == '__main__':
    main()