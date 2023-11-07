# Fine-tuning record
## First run
Successfully trained on Plachtaa's pretrained model, using Lifeiteng's training code. 
Several key things to notice:

## Run 2
- learning rate 1e-5
- warmup-epochs 0
- Trained AR, epoch 80, freeze ar_predict_layer only
- log_interval, valid_interval, checkpoint frequency and logic

| Phase      | loss | Top10Accuracy    |
| ----------- | ----------- | ----------- | 
| Train | 0.00257 (4.657/1813) | 0.5279 | 
| Valid | 0.00522 (4.909/941) | 0.4687 | 

## Implementation details
### prepare dataset
As lifeiteng uses Lhotse, we have to make our dataset something like libriTTS.
We also need to use its CutSet as dataset class, and its Sampler when constructing dataloader.

该repo使用了Ihotse进行数据处理, 也就是audio signal -> encodec的tokenize. 这是一个pipeline的module, 步骤是把wav准备成manifests, 然后manifests构建CutSet, CutSet中的Cut class可以load_audio. 最终的Dataset class是tokenizer script中指定的Unsupervised, 这个dataset会使用CutSet一个个load_audio.

我遇到的问题是在使用自己录音的dataset的时候, tokenizer无法padding. 经过研究发现, 每个audio都是类似(2, 12890), (2, 19088)...而pad之前的第一步本应该是squeeze sample, 按道理来说正常的input应该是(1, 12890), (1, 19088)..., 经过squeeze之后第一个dimension消失, 自然而然进入padding. 但是现在dimension上是2, 导致squeeze失败. 

为什么读进来的audip sample dimension 0是2呢? 经过研究发现这个dimension是代表channel的. 于是结合使用libritts的实验(数据处理没有任何问题), 发现是数据集里的音频有两个channel, 也就是所谓的stereo input双音道. 解决这个问题, 要么我们使用Encodec的48KHZ模式(可以处理stereo input), 要么用ffmpeg对数据集做一个转换处理. 后者更稳妥, 解决了数据处理的问题.

### GPU RAM
Bought Colab Pro. Met a incredibaly unsolvalble problem with K2 library, CUDA compiler, torch version and python version on AWS SageMaker. So AWS SageMaker, ****.

