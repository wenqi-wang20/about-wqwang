#!/usr/bin/env python3
"""
图片压缩脚本
自动压缩 gallery 文件夹中的所有图片并替换原始文件
支持 JPG, JPEG, PNG, WEBP 格式
"""

import os
import sys
from PIL import Image, ImageOps
import argparse


def compress_image(input_path, output_path=None, quality=85, max_size_mb=2.0):
    """
    压缩单个图片 - 保持原始比例，只降低文件大小

    Args:
        input_path: 输入图片路径
        output_path: 输出图片路径（如果为None则替换原图）
        quality: JPEG质量 (1-100)
        max_size_mb: 目标最大文件大小(MB)
    """
    try:
        # 打开图片
        with Image.open(input_path) as img:
            # 获取原始信息
            original_size = os.path.getsize(input_path)
            original_dimensions = img.size

            # 修正EXIF旋转信息
            img = ImageOps.exif_transpose(img)

            # 转换为RGB模式（如果是RGBA或其他模式）
            if img.mode in ('RGBA', 'LA', 'P'):
                # 创建白色背景
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()
                                 [-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # 设置输出路径
            if output_path is None:
                output_path = input_path

            # 保持原始尺寸，只调整质量来减小文件大小
            current_quality = quality
            target_size = max_size_mb * 1024 * 1024  # 转换为字节

            # 如果原文件已经很小且不需要格式转换，则跳过压缩
            if original_size <= target_size and output_path == input_path:
                print(f"⏭️  {os.path.basename(input_path)} 文件已经足够小，跳过压缩")
                return True

            # 保存压缩后的图片
            save_kwargs = {
                'format': 'JPEG',
                'quality': current_quality,
                'optimize': True
            }

            # 根据输出文件扩展名决定保存格式
            if output_path.lower().endswith('.png'):
                save_kwargs = {
                    'format': 'PNG',
                    'optimize': True
                }
                # PNG格式不支持quality参数，直接保存优化版本
                img.save(output_path, **save_kwargs)
            else:
                # 对于JPEG，尝试不同的质量设置来达到目标文件大小
                temp_path = output_path + '.temp'
                best_quality = current_quality

                # 尝试不同质量设置，找到合适的压缩级别
                quality_candidates = [
                    current_quality, 75, 65, 55, 45, 35, 30, 25, 20
                ]
                quality_candidates = list(dict.fromkeys(
                    q for q in quality_candidates if q <= current_quality
                ))

                for test_quality in quality_candidates:
                    test_kwargs = save_kwargs.copy()
                    test_kwargs['quality'] = test_quality
                    img.save(temp_path, **test_kwargs)
                    test_size = os.path.getsize(temp_path)

                    if test_size <= target_size or test_quality == quality_candidates[-1]:
                        best_quality = test_quality
                        break

                # 使用最佳质量保存最终文件
                final_kwargs = save_kwargs.copy()
                final_kwargs['quality'] = best_quality
                img.save(output_path, **final_kwargs)

                # 清理临时文件
                if os.path.exists(temp_path):
                    os.remove(temp_path)

            # 获取压缩后信息
            compressed_size = os.path.getsize(output_path)
            compression_ratio = (1 - compressed_size / original_size) * 100

            print(f"✅ {os.path.basename(input_path)}")
            print(
                f"   尺寸: {original_dimensions[0]}x{original_dimensions[1]} (保持不变)")
            print(
                f"   文件大小: {original_size / 1024:.1f} KB → {compressed_size / 1024:.1f} KB")
            print(f"   压缩率: {compression_ratio:.1f}%")
            if not output_path.lower().endswith('.png'):
                print(
                    f"   质量: {best_quality if 'best_quality' in locals() else current_quality}")
            print()

            return True

    except Exception as e:
        print(f"❌ 处理 {os.path.basename(input_path)} 时出错: {str(e)}")
        return False


def find_images(directory):
    """
    查找目录中的所有图片文件
    """
    image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'}
    image_files = []

    for root, dirs, files in os.walk(directory):
        for file in files:
            if any(file.lower().endswith(ext) for ext in image_extensions):
                image_files.append(os.path.join(root, file))

    return image_files


def main():
    parser = argparse.ArgumentParser(description='压缩gallery文件夹中的图片 - 保持原始比例')
    parser.add_argument('--gallery-dir', default='images/gallery',
                        help='Gallery目录路径 (默认: images/gallery)')
    parser.add_argument('--quality', type=int, default=85,
                        help='JPEG压缩质量 1-100 (默认: 85)')
    parser.add_argument('--max-size', type=float, default=2.0,
                        help='目标最大文件大小(MB) (默认: 2.0)')
    parser.add_argument('--dry-run', action='store_true',
                        help='预览模式，不实际修改文件')
    parser.add_argument('--convert-png-to-jpeg', action='store_true',
                        help='将PNG源图压缩为同名JPEG，并在成功后移除gallery中的PNG副本')

    args = parser.parse_args()

    # 检查gallery目录是否存在
    if not os.path.exists(args.gallery_dir):
        print(f"❌ 错误: 目录 {args.gallery_dir} 不存在")
        sys.exit(1)

    # 查找所有图片文件
    image_files = find_images(args.gallery_dir)

    if not image_files:
        print(f"❌ 在 {args.gallery_dir} 中没有找到图片文件")
        sys.exit(1)

    print(f"📂 在 {args.gallery_dir} 中找到 {len(image_files)} 个图片文件")
    print(f"⚙️  压缩设置: 质量={args.quality}, 最大文件大小={args.max_size}MB")
    print(f"📐 保持原始图片尺寸比例，只优化文件大小")
    if args.convert_png_to_jpeg:
        print("🖼️  PNG源图将转换为同名JPEG网页副本")

    if args.dry_run:
        print("🔍 预览模式 - 不会修改任何文件")

    print("=" * 60)

    # 处理每个图片
    success_count = 0
    total_original_size = 0
    total_compressed_size = 0

    for image_path in image_files:
        original_size = os.path.getsize(image_path)
        total_original_size += original_size

        if args.dry_run:
            status = "需要压缩" if original_size > args.max_size * 1024 * 1024 else "已经足够小"
            print(
                f"📋 预览: {os.path.basename(image_path)} ({original_size / 1024:.1f} KB) - {status}")
        else:
            output_path = image_path
            convert_png = (
                args.convert_png_to_jpeg
                and image_path.lower().endswith('.png')
            )
            if convert_png:
                output_path = os.path.splitext(image_path)[0] + '.jpg'

            if compress_image(
                    image_path,
                    output_path=output_path,
                    quality=args.quality,
                    max_size_mb=args.max_size):
                success_count += 1
                total_compressed_size += os.path.getsize(output_path)
                if convert_png:
                    os.remove(image_path)

    # 显示总结
    print("=" * 60)
    if args.dry_run:
        print(f"📊 预览完成: 找到 {len(image_files)} 个图片文件")
        print(f"📦 总大小: {total_original_size / 1024 / 1024:.1f} MB")
    else:
        print(f"📊 压缩完成: {success_count}/{len(image_files)} 个文件成功处理")
        print(f"📦 原始总大小: {total_original_size / 1024 / 1024:.1f} MB")
        print(f"📦 压缩后总大小: {total_compressed_size / 1024 / 1024:.1f} MB")
        if total_original_size > 0:
            total_compression = (
                1 - total_compressed_size / total_original_size) * 100
            print(f"📈 总压缩率: {total_compression:.1f}%")


if __name__ == "__main__":
    main()
