# Experiments Record #
### Lifeiteng ##
https://github.com/SyntheticSpeech/vall-e

Lifeiteng's implementation relies on Lhotse for its dataset preparation. Lhotse will process the audios into CutSet, and later a DynamicBucketSampler is used for constructing the dataloader.

One interesting bug we found is that we need to change our dataset to **mono**-channel, since Encodec uses **24KHZ** mono-channel. If stereo inputs are given, we need to use 49KHZ Encodec model.

No pretrained model is released for Lifeiteng's repo. We found a pioneer who trained on LibriTTS for 100 epoches, and continued our fine-tuning based on his checkpoint.

Problem:
- The checkpoint performance is very bad.
- On AWS, we met complex version problem brought by torch, nnCUDA, K2 and python version. Seems no easy workable solution can be found among them.

### Plachtaa ###
https://github.com/SyntheticSpeech/VALL-E-X

Checkout our fine-tune branch.

Plachtaa uses Lifeiteng's repo, and releases a super well-trained pretrained model. The only problem is that Plachtaa deleted all traing related codes, like dataset processing, training script and even model's forward pass.

There are differences between Plachtaa and Lifeiteng's implementation: Plachtaa supports multi-lingual by adding language embedding, uses different tokenizer and trained on different dataset.

We tried to re-write all these missing training codes, and runned our fine-tuning. Following sections summaries our experiments. We are still facing inference issue as generated audio is mainly noise, actively solving it now.

#### Implementation details
As lifeiteng uses Lhotse, we have to make our dataset something like libriTTS.
We also need to use its CutSet as dataset class, and its Sampler when constructing dataloader.

Lifeiteng and Plachtaa uses different **tokenizer**, resulting difference in **TextTokenCollator**

Lifeiteng Tokenize logic: text_prompt -> tokenizer (espeak) -> phonemes -> Collator (using precomputed SymbolTable) -> index sequence 

Plachtaa Tokenize logic: text_prompt -> Add language ID -> tokenizer (PhonemeBpeTokenizer, with pre-defined index mapping) -> index sequence directly, Collator just need to perform EOS/DOS/PAD

The most important thing to notice is that Plachtaa added language ID to text prompt:
```
text = "[EN]" + text + "[EN]"
```
Besides, phoneme index mapping is different. For example, PAD in PhonemeBpeTokenizer is 3, but in Lifeiteng's Tokenizer is 0.

In the model's **forward** pass, we added language embedding calculation accordingly.

#### First run
Successfully trained on Plachtaa's pretrained model, using Lifeiteng's training code. 
Several key things to notice:
- Prepare our dataset in LibriTTS format
- Using Lifeiteng's VALLE forward, but added language embedding
- Fixed embedding size in order to load Plachtaa's pretrained model
- Fixed erros in Checkpoint, training logic, data processing (collation), etc.
- Fixed inference script: it correctly produces good result if we directly use pretrained model

###### Run 2
- learning rate 1e-5
- warmup-epochs 0
- Trained AR, epoch 80, keep ar_predict_layer unfreezed
- log_interval, valid_interval, checkpoint frequency and logic

| Phase      | loss | Top10Accuracy    |
| ----------- | ----------- | ----------- | 
| Train | 4.657 | 0.5279 | 
| Valid | 4.909 | 0.4687 | 

#### Run 3
- Add language id "EN" to transcription, change to PhonemeBpeTokenizer text tokenizer in prepare stage
- learning rate 1e-6
- warmup-epochs 0
- Trained AR, epoch 80, keep ar_predict_layer unfreezed
- Trained NAR epoch 180, keep nar_predict_layers unfreezed

| Phase      | loss | Top10Accuracy    |
| ----------- | ----------- | ----------- | 
| AR Train |  4.967 | 0.4304 | 
| AR Valid |  4.914| 0.4665 | 
| NAR Train |  7.999 | 0.01076 | 
| NAR Valid |  7.79 | 0.01838 | 

#### Run 4
- Fixed wrong embedding used in AR forwarding
- learning rate 0.04 (ScaledAdam should be smart enough)
- warmup-epochs 200
- Trained AR, epoch 160, keep ar_predict_layer unfreezed

| Phase      | loss | Top10Accuracy    |
| ----------- | ----------- | ----------- | 
| AR Train |  4.765 | 0.4365 | 
| AR Valid |  4.763 | 0.4665 | 

#### Run 5
- Fixed forward logic: removed enrolled_len
- learning rate 1e-4, ScaledAdam
- warmup-epochs 200
- Trained AR, epoch 1000, keep ar_predict_layer unfreezed

| Phase      | loss | Top10Accuracy    |
| ----------- | ----------- | ----------- | 
| AR Train |  4.396 | 0.4497 | 
| AR Valid |  4.504 | 0.4697 | 

#### Run 6
- libriTTS dataset: dev-clean, test-clean (train cut 08:58:13, dev cut 00:47:31, test cut 08:34:09)
- learning rate 1e-5, ScaledAdam, warmup-epochs 200
- AR, 20 epochs, (did not include validation as valid_interval was wrong)

| Phase      | loss | Top10Accuracy    |
| ----------- | ----------- | ----------- | 
| AR Train |  5.748 | 0.1868 | 

#### Run 7
- learning rate 0.04, ScaledAdam, warmup-epochs 200
- AR 20 epochs, NAR 20 epochs

| Phase      | loss | Top10Accuracy    |
| ----------- | ----------- | ----------- | 
| AR Train |  5.748 | 0.1868 | 
| AR Valid |  5.923 | 0.1715 | 
| NAR Train | 5.669 | 0.2045 | 
| NAR Valid | 5.759  | 0.1858 | 


#### Run 8
- Shift adding language ID("[EN]") into tokenizer instead directly add it to raw text. We suspect adding language ID directly to raw .txt file might have a impact on CutSet dataset (who will try to match transcriptions and audios).
- Train only NAR, leaving AR freezed. Since the empty audio issue happend in AR: "VALL-E EOS [265 -> 311]". 20 epochs.

| Phase      | loss | Top10Accuracy    |
| ----------- | ----------- | ----------- | 
| NAR Train | 4.727 | 0.4219 | 
| NAR Valid | 5.292  | 0.4384 | 

Unfortunately it produces longer noise, but still noise :(

#### Run 9
- Since from Run 8's log, loss is still decreasing, so we tried 160 epochs. But did not solve the issue.

#### Run 10
- Add BOS and EOS in TextTokenizerCollator: The paper suggests that before we concate text prompt x and audio prompt c[:,1] for AR, we should append two special "<EOS>" tokens after each of them. However, due to the special BPE Tokenizer, Plachtaa did not do this (there is also no special phoneme ID for BOS and EOS). We manually add them in the collator.

#### Run 11
- Exclude prenet: It worked! This **solved** :milky_way: the AR forward issue, now correct audio output can be produced.

    Our command && param's default value should make add_prenet False, but due to some internal error in icefall's AttributeDict, this value is reset to true before constructing the model.

    Plachtaa's checkpoint **does not** have a prenet! That's why our AR forward produces noises or empty audio (just several frames), and the loss is so high: the prenet is a new prenet layer. 

Trained NAR for 20 epochs, lr 1e-6, warmup-steps 200
| Phase      | loss | Top10Accuracy    |
| ----------- | ----------- | ----------- | 
| NAR Train | 2.986 | 0.6734 | 
| NAR Valid | 2.69  | 0.7208 | 

#### Run 12
- Now we can conduct more experiments to improve the fine-tuning result. Observing from Run 11 that our loss is not changing as the learning rate is very small, we increase the value of learning rate to 1e-4 (AR) and 1e-3 (NAR) and turn off warmup.
- Also, we trained both AR(40 epochs) and NAR models (80 epochs)
- We set the accumulate-grad-steps to 2, compare to suggest value 6, it updates parameters more frequently. We changed this because our dataset is small. We can consider set it to 1 as well. 

| Phase      | loss | Top10Accuracy    |
| ----------- | ----------- | ----------- | 
| AR Train | 2.113  | 0.8455 | 
| AR Valid* | 2.292  | 0.7885 | 
| NAR Train | 2.332 | 0.8045 | 
| NAR Valid* | 2.542 | 0.7437 | 

*Note: due to wrong interval setting, validation are runned only 2 - 4 times, results might not be representative

- NAR is more difficult to train compare to AR. Why? One reason is certainly due to more predict layers, second reason we think is because "shared embedding". According to the paper, nar_audio_embedding share the **same parameters** as nar_predict_layers. We turn off sharing.
- We also observe that turn warmup on with learning rate 0.04 will quickly allow us to reach traing Top10 accuracy > **95%** !

NAR trained base on same trained AR as above
| Phase      | loss | Top10Accuracy    |
| ----------- | ----------- | ----------- |
| NAR Train | 0.766 | 0.9852 | 
| NAR Valid* | 3.503 | 0.6532 | 

*Note: same reason as above, the validation only happened at epoch 40