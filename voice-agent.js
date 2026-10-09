/* Main voice mode. Load after app.js, which retains the classic fallback. */
import { Conversation } from '@elevenlabs/client';

const classicStart = startConversation;
const classicStop = stopConversation;
let agentConversation = null;
let agentReservation = null;
let agentTimer = null;

function reconcileAgent(id, reservation) {
  if (!id || !reservation) return;
  // Call details can take a moment to finalize. Keep the full reservation until confirmed.
  const settle = () => fetch('api/agents/settle', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ conversation_id: id, reservation }), keepalive: true,
  }).then((response) => response.json()).catch(() => ({}));
  let attempts = 0;
  const retry = () => settle().then((result) => {
    if (!result.settled && ++attempts < 6) setTimeout(retry, 5000);
  });
  retry();
}

stopConversation = function () {
  const agent = agentConversation;
  const reservation = agentReservation;
  agentConversation = null;
  agentReservation = null;
  clearTimeout(agentTimer);
  if (conversationState?.backend === 'agents') conversationState = null;
  classicStop();
  if (agent) {
    const id = agent.getId();
    agent.endSession().finally(() => reconcileAgent(id, reservation)).catch(() => {});
  }
};

startConversation = async function () {
  if (!guardBooks(selectedPeople())) return;
  const request = ++conversationRequest;
  conversationConnecting = true;
  setTalkState('thinking');
  setLiveTranscript('');
  setHomeStatus('');
  $('talk-button').innerHTML = 'Gespräch beenden';
  let config;
  try {
    const response = await fetch('api/agents/session', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profiles: selectedPeople(), voice: state.voiceGender }),
    });
    config = await response.json();
    if (!response.ok) throw new Error(config.error || 'Das Gespräch konnte nicht gestartet werden.');
    if (request !== conversationRequest) return;
    if (config.backend !== 'agents') {
      if (AUTH.enabled) throw new Error('Der überprüfte Gesprächsdienst ist gerade nicht verfügbar. Bitte später erneut versuchen.');
      document.documentElement.dataset.voiceBackend = 'classic';
      conversationConnecting = false;
      await classicStart();
      return;
    }
    document.documentElement.dataset.voiceBackend = 'agents';
    let receivedMode = false;
    const agent = await Conversation.startSession({
      ...(config.signed_url ? { signedUrl: config.signed_url, connectionType: 'websocket' }
        : { conversationToken: config.token, connectionType: 'webrtc' }),
      dynamicVariables: { profiles: config.profiles, group_rules: config.group_rules, greeting: config.greeting },
      overrides: { tts: { voiceId: config.voice_id } },
      onIncomingEvent: (event) => {
        if (request !== conversationRequest) return;
        if (event.type === 'tentative_user_transcript') {
          setTalkState('idle');
          setLiveTranscript(event.tentative_user_transcription_event?.user_transcript || '', true);
        }
      },
      onMessage: ({ message, source }) => {
        if (request !== conversationRequest) return;
        setLiveTranscript(message || '');
        const role = source === 'user' ? 'user' : 'assistant';
        if (role === 'user') setTalkState('thinking');
        if (message) conversationMessages = [...conversationMessages, { role, content: message }].slice(-8);
      },
      onModeChange: ({ mode }) => {
        if (request !== conversationRequest) return;
        receivedMode = true;
        setTalkState(mode === 'speaking' ? 'talking' : 'idle');
        $('talk-button').classList.toggle('is-recording', mode === 'listening');
      },
      onDisconnect: () => {
        if (request !== conversationRequest) return;
        stopConversation();
      },
      onError: () => {
        if (request !== conversationRequest) return;
        stopConversation();
        setHomeError();
      },
    });
    if (request !== conversationRequest) {
      const id = agent.getId();
      await agent.endSession();
      reconcileAgent(id, config.reservation);
      return;
    }
    agentConversation = agent;
    agentReservation = config.reservation;
    conversationState = { backend: 'agents' };
    conversationConnecting = false;
    if (!receivedMode) setTalkState('idle');
    $('talk-button').classList.add('is-recording');
    agentTimer = setTimeout(() => {
      stopConversation();
      if (config.guest) setHomeError('Die fünf Minuten zum Ausprobieren sind aufgebraucht. Über «Angehörige» können Sie sich anmelden und weitersprechen.');
    }, config.max_seconds * 1000);
  } catch (error) {
    if (request !== conversationRequest) return;
    stopConversation();
    setHomeError(error.message);
  }
};
