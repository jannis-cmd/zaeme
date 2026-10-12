/* Browser-local PCM capture. Audio is sent only while the conversation is active. */
class ZaemeCapture extends AudioWorkletProcessor {
  constructor() {
    super();
    this.samples = [];
    this.chunkSize = Math.round(sampleRate / 5);
  }

  process(inputs, outputs) {
    const input = inputs[0]?.[0];
    for (const channel of outputs[0] || []) channel.fill(0);
    if (!input) return true;
    for (let i = 0; i < input.length; i++) this.samples.push(input[i]);
    if (this.samples.length >= this.chunkSize) {
      const pcm = new Int16Array(this.samples.length);
      for (let i = 0; i < this.samples.length; i++) {
        const value = Math.max(-1, Math.min(1, this.samples[i]));
        pcm[i] = value < 0 ? value * 32768 : value * 32767;
      }
      this.samples = [];
      this.port.postMessage(pcm.buffer, [pcm.buffer]);
    }
    return true;
  }
}

registerProcessor("zaeme-capture", ZaemeCapture);
