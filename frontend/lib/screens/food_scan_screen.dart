import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import '../services/food_scan_service.dart';
import '../models/food_scan_result.dart';
import '../widgets/loading_button.dart';
import 'food_result_screen.dart';

class FoodScanScreen extends StatefulWidget {
  const FoodScanScreen({super.key});

  @override
  State<FoodScanScreen> createState() => _FoodScanScreenState();
}

class _FoodScanScreenState extends State<FoodScanScreen> {
  final _service = FoodScanService();
  final _picker  = ImagePicker();

  File?  _selectedImage;
  bool   _analyzing = false;
  String? _error;

  Future<void> _pickImage(ImageSource source) async {
    try {
      final picked = await _picker.pickImage(
        source: source,
        imageQuality: 90,
        maxWidth: 1920,
      );
      if (picked != null) {
        setState(() {
          _selectedImage = File(picked.path);
          _error = null;
        });
      }
    } catch (e) {
      setState(() => _error = 'Could not access camera/gallery: $e');
    }
  }

  Future<void> _analyze() async {
    if (_selectedImage == null) {
      setState(() => _error = 'Please select or capture an image first.');
      return;
    }
    setState(() { _analyzing = true; _error = null; });

    try {
      final data = await _service.analyzeFoodLabel(_selectedImage!);
      final result = FoodScanResult.fromJson(data);
      if (mounted) {
        Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => FoodResultScreen(result: result)),
        );
      }
    } catch (e) {
      setState(() => _error = e.toString().replaceAll('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _analyzing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: const Text('Scan Food Label')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Title
            Text('Packaged Food Scanner',
                style: Theme.of(context)
                    .textTheme
                    .headlineSmall
                    ?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            Text(
              'Take a photo of a food label or upload from gallery. '
              'We\'ll check it against your health profile.',
              style: Theme.of(context)
                  .textTheme
                  .bodyMedium
                  ?.copyWith(color: Colors.grey[600]),
            ),
            const SizedBox(height: 24),

            // Image preview
            AnimatedContainer(
              duration: const Duration(milliseconds: 300),
              height: 240,
              decoration: BoxDecoration(
                color: cs.surfaceContainerHighest,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: _selectedImage != null
                      ? cs.primary
                      : cs.outlineVariant,
                  width: 2,
                ),
              ),
              child: _selectedImage != null
                  ? ClipRRect(
                      borderRadius: BorderRadius.circular(14),
                      child: Image.file(_selectedImage!, fit: BoxFit.cover,
                          width: double.infinity),
                    )
                  : Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.image_outlined,
                            size: 64, color: cs.outlineVariant),
                        const SizedBox(height: 12),
                        Text('No image selected',
                            style: TextStyle(color: Colors.grey[500])),
                      ],
                    ),
            ),
            const SizedBox(height: 20),

            // Camera and gallery buttons
            Row(children: [
              Expanded(
                child: OutlinedButton.icon(
                  icon: const Icon(Icons.camera_alt),
                  label: const Text('Camera'),
                  onPressed: _analyzing
                      ? null
                      : () => _pickImage(ImageSource.camera),
                  style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 14)),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: OutlinedButton.icon(
                  icon: const Icon(Icons.photo_library),
                  label: const Text('Gallery'),
                  onPressed: _analyzing
                      ? null
                      : () => _pickImage(ImageSource.gallery),
                  style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 14)),
                ),
              ),
            ]),
            const SizedBox(height: 16),

            // Error message
            if (_error != null) ...[
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.errorContainer,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Row(children: [
                  Icon(Icons.error_outline,
                      color: Theme.of(context).colorScheme.onErrorContainer,
                      size: 20),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(_error!,
                        style: TextStyle(
                            color: Theme.of(context)
                                .colorScheme
                                .onErrorContainer)),
                  ),
                ]),
              ),
              const SizedBox(height: 16),
            ],

            // Analyze button
            LoadingButton(
              loading: _analyzing,
              label: 'Analyze Food Label',
              onPressed: _analyze,
            ),
            const SizedBox(height: 24),

            // Tips card
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('📸 Tips for better results',
                        style: Theme.of(context)
                            .textTheme
                            .titleSmall
                            ?.copyWith(fontWeight: FontWeight.bold)),
                    const SizedBox(height: 8),
                    ...[
                      'Ensure the ingredients list is clearly visible',
                      'Good lighting helps — avoid shadows on the label',
                      'Hold the camera steady for a sharp image',
                      'Capture the full nutrition facts panel if possible',
                    ].map((tip) => Padding(
                          padding: const EdgeInsets.symmetric(vertical: 3),
                          child: Row(children: [
                            Icon(Icons.check_circle_outline,
                                size: 16, color: cs.primary),
                            const SizedBox(width: 8),
                            Expanded(
                                child: Text(tip,
                                    style: const TextStyle(fontSize: 13))),
                          ]),
                        )),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
