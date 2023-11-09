# Fine-tuning record
## First run
Successfully trained on Plachtaa's pretrained model, using Lifeiteng's training code. 
Several key things to notice:
- Prepare our dataset in LibriTTS format
- Using Lifeiteng's VALLE forward, but added language embedding
- Fixed embedding size in order to load Plachtaa's pretrained model
- Fixed erros in Checkpoint, training logic, data processing (collation), etc.
- Fixed inference script: it correctly produces good result if we directly use pretrained model

## Run 2
- learning rate 1e-5
- warmup-epochs 0
- Trained AR, epoch 80, keep ar_predict_layer unfreezed
- log_interval, valid_interval, checkpoint frequency and logic

| Phase      | loss | Top10Accuracy    |
| ----------- | ----------- | ----------- | 
| Train | 4.657 | 0.5279 | 
| Valid | 4.909 | 0.4687 | 

## Run 3
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

## Run 4
- Fixed wrong embedding used in AR forwarding
- learning rate 0.04 (ScaledAdam should be smart enough)
- warmup-epochs 200
- Trained AR, epoch 160, keep ar_predict_layer unfreezed

| Phase      | loss | Top10Accuracy    |
| ----------- | ----------- | ----------- | 
| AR Train |  4.765 | 0.4365 | 
| AR Valid |  4.763 | 0.4665 | 

## Run 5
- Fixed forward logic: removed enrolled_len
- learning rate 1e-4, ScaledAdam
- warmup-epochs 200
- Trained AR, epoch 1000, keep ar_predict_layer unfreezed

| Phase      | loss | Top10Accuracy    |
| ----------- | ----------- | ----------- | 
| AR Train |  4.396 | 0.4497 | 
| AR Valid |  4.504 | 0.4697 | 

## Run 6
- libriTTS dataset: dev-clean, test-clean (train cut 08:58:13, dev cut 00:47:31, test cut 08:34:09)
- learning rate 1e-5, ScaledAdam, warmup-epochs 200
- AR, 20 epochs, (did not include validation as valid_interval was wrong)

| Phase      | loss | Top10Accuracy    |
| ----------- | ----------- | ----------- | 
| AR Train |  5.748 | 0.1868 | 

## Run 7
- learning rate 0.04, ScaledAdam, warmup-epochs 200
- AR 20 epochs, NAR 20 epochs

| Phase      | loss | Top10Accuracy    |
| ----------- | ----------- | ----------- | 
| AR Train |  5.748 | 0.1868 | 
| AR Valid |  5.923 | 0.1715 | 
| NAR Train | 5.669 | 0.2045 | 
| NAR Valid | 5.759  | 0.1858 | 

## Implementation details
### prepare dataset
As lifeiteng uses Lhotse, we have to make our dataset something like libriTTS.
We also need to use its CutSet as dataset class, and its Sampler when constructing dataloader.

该repo使用了Ihotse进行数据处理, 也就是audio signal -> encodec的tokenize. 这是一个pipeline的module, 步骤是把wav准备成manifests, 然后manifests构建CutSet, CutSet中的Cut class可以load_audio. 最终的Dataset class是tokenizer script中指定的Unsupervised, 这个dataset会使用CutSet一个个load_audio.

我遇到的问题是在使用自己录音的dataset的时候, tokenizer无法padding. 经过研究发现, 每个audio都是类似(2, 12890), (2, 19088)...而pad之前的第一步本应该是squeeze sample, 按道理来说正常的input应该是(1, 12890), (1, 19088)..., 经过squeeze之后第一个dimension消失, 自然而然进入padding. 但是现在dimension上是2, 导致squeeze失败. 

为什么读进来的audip sample dimension 0是2呢? 经过研究发现这个dimension是代表channel的. 于是结合使用libritts的实验(数据处理没有任何问题), 发现是数据集里的音频有两个channel, 也就是所谓的stereo input双音道. 解决这个问题, 要么我们使用Encodec的48KHZ模式(可以处理stereo input), 要么用ffmpeg对数据集做一个转换处理. 后者更稳妥, 解决了数据处理的问题.

### GPU RAM
Bought Colab Pro. Met a incredibaly unsolvalble problem with K2 library, CUDA compiler, torch version and python version on AWS SageMaker. So AWS SageMaker, ****.

### Tokenizer
Lifeiteng and Plachtaa uses different tokenizer, resulting difference in TextTokenCollator

Lifeiteng Tokenize logic: text_prompt -> tokenizer (espeak) -> phonemes -> Collator (using precomputed SymbolTable) -> index sequence 

Plachtaa Tokenize logic: text_prompt -> Add language ID -> tokenizer (PhonemeBpeTokenizer, with pre-defined index mapping) -> index sequence directly, Collator just need to perform EOS/DOS/PAD

The most important thing to notice is that Plachtaa added language ID to text prompt:
```
text = "[EN]" + text + "[EN]"
```
Besides, phoneme index mapping is different. For example, PAD in PhonemeBpeTokenizer is 3, but in Lifeiteng's Tokenizer is 0.



