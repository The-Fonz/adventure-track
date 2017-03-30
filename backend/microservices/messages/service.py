


class MessageService:
    "Nameko service"

    name = "message_service"

    db = Session(Base)

    def get_messages(self, user_id):
        "Get all messages of one user"
        q = self.db.query(Message).filter(Message.user_id == user_id)
        return q.all()

    def emit_message(self, message_id):
        """
        Notify all browser listeners of new message. Also called for media update,
        so that msg in browser is overwritten with new info.
        """
        m = self.db.query(Message).get(message_id)
        # TODO: websocket call

    @rpc
    def add_message(self, user_id, timestamp, title=None, text=None, image_original=None, video_original=None, audio_original=None):
        "Add message to db"
        m = Message(user_id=user_id, timestamp=timestamp,
                    title=title, text=text,
                    image_original=image_original,
                    video_original=video_original,
                    audio_original=audio_original)
        self.db.add(m)
        self.db.commit()
        # Message id must later be passed to self.add_media_detail
        message_id = m.id
        # Notify listeners of new message
        self.emit_message(message_id)
        # Start transcoding tasks
        if image_original:
            # TODO: start task with args = [message_id, originalpath]
            pass
        if video_original:
            pass
        if audio_original:
            pass

    @rpc
    def add_media_detail(self, message_id,
                         image_versions=None,
                         video_versions=None,
                         audio_versions=None):
        "Should be called by media convert task"
        msg = self.db.query(Message).get(message_id)
        if image_versions:
            msg.image_versions = image_versions
        if video_versions:
            msg.video_versions = video_versions
        if audio_versions:
            msg.audio_versions = audio_versions
        # Emit update so that browser can render new media types
        self.emit_message(message_id)


@pytest.mark.parametrize('base', [Base])
def test_service(testsession):
    from datetime import datetime
    t = datetime.now()
    ls = worker_factory(MessageService, db=testsession)
    # Message without media
    ls.add_message(20, t, title='Testmsgtitle', text='Hi there.')
    msg = ls.get_messages(20)[0]
    assert msg.title == 'Testmsgtitle'
    assert msg.text  == 'Hi there.'
    # Omit title and text, should warn
    with pytest.raises(Warning):
        ls.add_message(1, t)
